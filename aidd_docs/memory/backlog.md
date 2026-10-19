# Backlog

## Supports

| Support | Authority for | Role |
| --- | --- | --- |
| GitHub Issues | epics, stories, tasks, bugs, spikes | source de vérité du travail prévu |
| GitHub Project | statut | tableau de suivi |

## Representation

| Artifact | Support | Native representation |
| --- | --- | --- |
| Epic | GitHub Issues | label `epic` |
| User Story | GitHub Issues | label `story` |
| Task | GitHub Issues | label `task` |
| Defect | GitHub Issues | label `bug` |
| Spike | GitHub Issues | label `spike` |

## Workflow

| Support | Native status | Meaning |
| --- | --- | --- |
| GitHub Project | Todo | prêt, pas commencé |
| GitHub Project | In progress | en cours |
| GitHub Project | Done | livré |

## Relations

- Parent: sous-issue GitHub sous l'epic
- Dependency: mention « bloqué par #n » dans l'issue
