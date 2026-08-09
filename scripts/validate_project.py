#!/usr/bin/env python3

from __future__ import annotations

import math
import pathlib
import sys
from typing import Optional


REQUIRED_KEYS = {
    "events",
    "threads",
    "seed_base",
    "physics_list",
    "output",
}

ALLOWED_KEYS = REQUIRED_KEYS | {
    "generator_mode",
    "first_bcid",
    "interaction_mode",
    "mean_interactions",
    "fixed_interactions",
    "pythia_config",
    "production_cut_mm",
    "beam_sigma_x_mm",
    "beam_sigma_y_mm",
    "beam_sigma_z_mm",
    "beam_sigma_t_ns",
    "max_abs_eta",
    "transport_neutrinos",
    "generator_audit",
    "check_overlaps",
    "print_every",
    "single_particle_pdg",
    "single_particle_kinetic_energy_gev",
    "single_particle_eta",
    "single_particle_phi",
}

BOOLEAN_VALUES = {"true", "yes", "1", "false", "no", "0"}


def parse_int(values: dict[str, str], key: str, fallback: Optional[str] = None) -> int:
    raw = values.get(key, fallback)
    if raw is None:
        raise ValueError(f"chave obrigatória ausente: {key}")
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"valor inteiro inválido para {key}: {raw}") from error


def parse_float(
    values: dict[str, str], key: str, fallback: Optional[str] = None
) -> float:
    raw = values.get(key, fallback)
    if raw is None:
        raise ValueError(f"chave obrigatória ausente: {key}")
    try:
        result = float(raw)
    except ValueError as error:
        raise ValueError(f"valor numérico inválido para {key}: {raw}") from error
    if not math.isfinite(result):
        raise ValueError(f"{key} deve ser finito")
    return result


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
    unknown = sorted(values.keys() - ALLOWED_KEYS)
    if unknown:
        raise ValueError("chaves desconhecidas: " + ", ".join(unknown))

    generator_mode = values.get("generator_mode", "pythia")
    if generator_mode not in {"pythia", "single_particle"}:
        raise ValueError("generator_mode deve ser 'pythia' ou 'single_particle'")

    mode_required = (
        {"interaction_mode", "mean_interactions", "pythia_config"}
        if generator_mode == "pythia"
        else {
            "single_particle_pdg",
            "single_particle_kinetic_energy_gev",
            "single_particle_eta",
            "single_particle_phi",
        }
    )
    missing = sorted(mode_required - values.keys())
    if missing:
        raise ValueError("chaves obrigatórias ausentes: " + ", ".join(missing))

    interaction_mode = values.get("interaction_mode", "poisson")
    if interaction_mode not in {"poisson", "fixed"}:
        raise ValueError("interaction_mode deve ser 'poisson' ou 'fixed'")

    events = parse_int(values, "events")
    first_bcid = parse_int(values, "first_bcid", "0")
    if events <= 0:
        raise ValueError("events deve ser positivo")
    if first_bcid < 0 or first_bcid + events - 1 > 2_147_483_647:
        raise ValueError("o intervalo de BCIDs deve caber em um inteiro não negativo")
    if parse_int(values, "threads") <= 0:
        raise ValueError("threads deve ser positivo")
    if parse_int(values, "seed_base") <= 0:
        raise ValueError("seed_base deve ser positivo")
    if parse_float(values, "mean_interactions", "1.0") < 0.0:
        raise ValueError("mean_interactions não pode ser negativo")
    if parse_int(values, "fixed_interactions", "1") < 0:
        raise ValueError("fixed_interactions não pode ser negativo")
    if parse_float(values, "production_cut_mm", "1.0") <= 0.0:
        raise ValueError("production_cut_mm deve ser positivo")
    for key in (
        "beam_sigma_x_mm",
        "beam_sigma_y_mm",
        "beam_sigma_z_mm",
        "beam_sigma_t_ns",
    ):
        if parse_float(values, key, "0.0") < 0.0:
            raise ValueError(f"{key} não pode ser negativo")
    max_abs_eta = parse_float(values, "max_abs_eta", "1.8")
    if not 0.0 < max_abs_eta <= 1.8:
        raise ValueError("max_abs_eta deve estar em (0, 1.8]")
    if generator_mode == "single_particle":
        if parse_int(values, "single_particle_pdg") == 0:
            raise ValueError("single_particle_pdg não pode ser zero")
        if parse_float(values, "single_particle_kinetic_energy_gev") <= 0.0:
            raise ValueError(
                "single_particle_kinetic_energy_gev deve ser positiva"
            )
        if abs(parse_float(values, "single_particle_eta")) > max_abs_eta:
            raise ValueError("single_particle_eta deve respeitar max_abs_eta")
        particle_phi = parse_float(values, "single_particle_phi")
        if not -math.pi <= particle_phi <= math.pi:
            raise ValueError(
                "single_particle_phi deve estar no intervalo [-pi, pi]"
            )
    if parse_int(values, "print_every", "10") <= 0:
        raise ValueError("print_every deve ser positivo")
    for key in ("transport_neutrinos", "generator_audit", "check_overlaps"):
        value = values.get(key, "false").lower()
        if value not in BOOLEAN_VALUES:
            raise ValueError(f"valor booleano inválido para {key}: {value}")

    if generator_mode == "pythia":
        pythia_path = pathlib.Path(values["pythia_config"])
        if not pythia_path.is_absolute():
            pythia_path = config_path.parent / pythia_path
        pythia_text = pythia_path.read_text(encoding="utf-8")
        active_commands = []
        for raw_line in pythia_text.splitlines():
            line = raw_line.split("!", 1)[0].split("#", 1)[0].strip()
            if line:
                key, separator, value = line.partition("=")
                active_commands.append(
                    f"{key.strip()} = {value.strip()}"
                    if separator
                    else " ".join(line.split())
                )
        active_text = "\n".join(active_commands)

        required_commands = (
            "Beams:idA = 2212",
            "Beams:idB = 2212",
            "Beams:eCM = 14000.",
            "SoftQCD:inelastic = on",
        )
        for command in required_commands:
            if command not in active_text:
                raise ValueError(f"comando PYTHIA obrigatório ausente: {command}")

        if "SoftQCD:all = on" in active_text:
            raise ValueError(
                "SoftQCD:all inclui espalhamento elástico; use inelastic"
            )

    print(f"Configuração válida: {config_path}")
    print(f"Modo do gerador: {generator_mode}")
    if generator_mode == "pythia":
        print(f"Arquivo PYTHIA: {pythia_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
