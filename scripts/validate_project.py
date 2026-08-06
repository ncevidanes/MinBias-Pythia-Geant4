#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import sys


REQUIRED_KEYS = {
    "events",
    "threads",
    "seed_base",
    "interaction_mode",
    "mean_interactions",
    "pythia_config",
    "physics_list",
    "output",
}


def parse_config(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: esperado 'chave = valor'")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or not value:
            raise ValueError(f"{path}:{number}: chave ou valor vazio")
        if key in values:
            raise ValueError(f"{path}:{number}: chave duplicada: {key}")
        values[key] = value
    return values


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: validate_project.py CONFIG", file=sys.stderr)
        return 2

    config_path = pathlib.Path(sys.argv[1]).resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)

    values = parse_config(config_path)
    missing = sorted(REQUIRED_KEYS - values.keys())
    if missing:
        raise ValueError("chaves obrigatórias ausentes: " + ", ".join(missing))

    if values["interaction_mode"] not in {"poisson", "fixed"}:
        raise ValueError("interaction_mode deve ser 'poisson' ou 'fixed'")

    if int(values["events"]) <= 0:
        raise ValueError("events deve ser positivo")
    if int(values["threads"]) <= 0:
        raise ValueError("threads deve ser positivo")
    if float(values["mean_interactions"]) < 0:
        raise ValueError("mean_interactions não pode ser negativo")

    pythia_path = pathlib.Path(values["pythia_config"])
    if not pythia_path.is_absolute():
        pythia_path = config_path.parent / pythia_path
    pythia_text = pythia_path.read_text(encoding="utf-8")

    required_commands = (
        "Beams:idA = 2212",
        "Beams:idB = 2212",
        "Beams:eCM = 14000.",
        "SoftQCD:inelastic = on",
    )
    for command in required_commands:
        if command not in pythia_text:
            raise ValueError(f"comando PYTHIA obrigatório ausente: {command}")

    if "SoftQCD:all = on" in pythia_text:
        raise ValueError("SoftQCD:all inclui espalhamento elástico; use inelastic")

    print(f"Configuração válida: {config_path}")
    print(f"Arquivo PYTHIA: {pythia_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

