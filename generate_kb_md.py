#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate tech-support KB markdown files via OpenAI API.

Default output folder:
  data/kb_docs/

Usage:
  pip install openai pydantic python-dotenv
  export OPENAI_API_KEY="..."
  python generate_kb_md.py --total 100 --outdir data/kb_docs --model gpt-4o-mini
"""

from __future__ import annotations

import os
import re
import json
import time
import argparse
from typing import List, Dict

from pydantic import BaseModel, Field
from openai import OpenAI


# -------- Structured schema --------
class KBStep(BaseModel):
    title: str
    commands: List[str] = Field(default_factory=list)
    explanation: str


class KBArticle(BaseModel):
    title: str
    category: str
    tags: List[str] = Field(default_factory=list)

    symptoms: List[str]
    root_causes: List[str]
    solution_steps: List[KBStep]
    verification: List[str]
    escalation_request: List[str]

    # Human-readable Markdown article
    markdown: str


DEFAULT_TOPICS: Dict[str, List[str]] = {
    "docker": [
        "Cannot connect to the Docker daemon at unix:///var/run/docker.sock",
        "Permission denied при доступе к /var/run/docker.sock",
        "bind: address already in use при запуске контейнера",
        "docker compose: command not found / несовместимые версии compose",
        "Volume permission issues при работе с файлами на хосте",
        "Контейнер постоянно перезапускается (CrashLoop-like)",
        "Ошибка 'no space left on device' при сборке/запуске",
    ],
    "nginx": [
        "502 Bad Gateway при проксировании на FastAPI (uvicorn)",
        "Nginx reload не применяет конфиг / конфиг не читается",
        "Проблемы SSL: истёк сертификат / неверная цепочка",
        "upstream prematurely closed connection while reading response header",
        "Статика не отдается (location /static)",
        "Слишком большой body (413 Request Entity Too Large)",
        "Redirect loop (too many redirects)",
    ],
    "fastapi": [
        "Uvicorn падает: ModuleNotFoundError / ImportError",
        "CORS ошибка между фронтендом и FastAPI",
        "Timeout / зависание запросов (workers, keep-alive)",
        "422 ValidationError из-за схемы запроса",
        "Ошибка при загрузке файлов (multipart/form-data)",
        "WebSocket не работает через reverse proxy",
        "Background tasks не выполняются/теряются",
    ],
    "postgres": [
        "Connection refused к PostgreSQL из Docker контейнера",
        "FATAL: password authentication failed",
        "Медленная выборка / нет индекса / плохой план",
        "too many connections / exhausted connections",
        "Проблемы миграций/схем (search_path)",
        "deadlock detected",
        "SSL required / no pg_hba.conf entry",
    ],
    "alembic": [
        "Alembic revision есть, но таблицы не создаются",
        "Target database is not up to date",
        "Multiple heads detected",
        "autogenerate не видит модели (metadata пустой)",
        "env.py использует не тот URL БД",
        "Ошибка при downgrade/upgrade (constraint already exists)",
        "Миграции применяются в другую схему",
    ],
    "python_env": [
        "pip ставит пакеты не в то окружение (venv/poetry)",
        "ModuleNotFoundError после установки зависимостей",
        "Конфликт версий зависимостей после обновления",
        "Ошибки при сборке wheels (gcc/headers) на Linux",
        "Не совпадают версии Python (3.10 vs 3.11)",
        "ssl module missing / certificate verify failed",
        "Permission denied при установке пакетов",
    ],
    "git_ci": [
        "Git push rejected (non-fast-forward / protected branch)",
        "SSH key authentication failed",
        "GitHub Actions: python version not found / cache issues",
        "CI падает на lint/tests только в pipeline",
        "Submodule не подтягивается в CI",
        "Permission denied на deploy step",
        "Secrets не доступны в PR from fork",
    ],
    "network": [
        "DNS не резолвится в контейнере",
        "Timeout при обращении к внешнему API",
        "Firewall блокирует порт приложения",
        "CORS/CSRF проблемы в браузере",
        "Proxy environment variables мешают",
        "TLS handshake failed",
        "Webhooks не доходят (ingress/ports)",
    ],
    "linux": [
        "Permission denied на запись в директорию проекта",
        "systemd service не стартует / падает",
        "Логи растут и забивают диск (logrotate)",
        "Порт занят неизвестным процессом",
        "Проблемы времени/часового пояса",
        "Ошибки прав на сокеты/пайпы",
        "SELinux/AppArmor блокирует доступ",
    ],
    "wsl_windows": [
        "Docker Desktop + WSL2 не запускается",
        "Не работает copy/paste в терминале",
        "Permission/line endings проблемы между Windows и WSL",
        "Port forwarding WSL: сервис не доступен с Windows",
        "Python/venv конфликт в WSL",
        "Проблемы с путями /mnt/c",
        "WSL не видит интернет/ DNS",
    ],
}


def slugify(text: str, max_len: int = 70) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9а-яё]+", "-", text, flags=re.IGNORECASE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "article"


def build_prompt(category: str, topic: str) -> List[dict]:
    system = (
        "Ты инженер технической поддержки. Сгенерируй статью базы знаний (KB) в формате Markdown.\n"
        "Язык: русский.\n\n"
        "Структура Markdown строго такая:\n"
        "# <Title>\n"
        "## Симптомы\n"
        "- ...\n"
        "## Возможные причины\n"
        "- ...\n"
        "## Решение (пошагово)\n"
        "1. **Шаг** — описание\n"
        "   ```bash\n"
        "   <команды>\n"
        "   ```\n"
        "## Проверка\n"
        "- ...\n"
        "## Если не помогло — пришлите\n"
        "- ...\n\n"
        "Правила:\n"
        "- 3–7 шагов решения.\n"
        "- Команды должны быть безопасными (не удалять данные, не использовать rm -rf).\n"
        "- Учитывай, что пользователь может быть на Windows/WSL/macOS/Linux — если важно, добавь развилки.\n"
        "- Добавляй конкретику (имена сервисов, типовые пути, команды диагностики).\n"
        "- Верни structured output по схеме.\n"
    )
    user = f"Категория: {category}\nСитуация: {topic}\nСгенерируй KB-статью."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_one(client: OpenAI, model: str, category: str, topic: str) -> KBArticle:
    resp = client.responses.parse(
        model=model,
        input=build_prompt(category, topic),
        text_format=KBArticle,
    )
    return resp.output_parsed


def distribute_total(total: int, categories: List[str]) -> Dict[str, int]:
    base = total // len(categories)
    rem = total % len(categories)
    out = {c: base for c in categories}
    for i in range(rem):
        out[categories[i]] += 1
    return out


def ensure_outdir(outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Generate 100 KB markdown articles via OpenAI API.")
    ap.add_argument("--model", default=os.getenv("OPENAI_GEN_MODEL", "gpt-4o-mini"))
    ap.add_argument("--total", type=int, default=100)
    ap.add_argument("--categories", default="docker,nginx,fastapi,postgres,alembic,python_env,git_ci,network,linux,wsl_windows")
    ap.add_argument("--outdir", default="data/kb_docs")
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if args.total < len(categories):
        raise ValueError(f"--total must be >= number of categories ({len(categories)})")

    plan = distribute_total(args.total, categories)
    ensure_outdir(args.outdir)

    client = OpenAI()

    index = []
    counter = 0

    for cat in categories:
        topics = DEFAULT_TOPICS.get(cat, [f"Типовая проблема для {cat}"])
        need = plan[cat]

        for i in range(need):
            topic = topics[i % len(topics)]
            counter += 1
            print(f"[GEN {counter:03d}/{args.total}] {cat}: {topic}")

            t0 = time.time()
            article = generate_one(client, args.model, cat, topic)
            dt = time.time() - t0

            slug = slugify(article.title)
            fname = f"{cat}__{counter:03d}__{slug}.md"
            path = os.path.join(args.outdir, fname)

            with open(path, "w", encoding="utf-8") as f:
                f.write(article.markdown.strip() + "\n")

            index.append({
                "file": fname,
                "title": article.title,
                "category": article.category,
                "tags": article.tags,
                "seed_topic": topic,
                "model": args.model,
                "generated_at_unix": int(time.time()),
                "gen_seconds": round(dt, 3),
            })

            print(f"[OK] {fname} ({dt:.2f}s)")
            time.sleep(args.sleep)

    with open(os.path.join(args.outdir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\nDONE. Generated {len(index)} markdown articles in: {args.outdir}/")


if __name__ == "__main__":
    main()
