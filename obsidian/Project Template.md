---
tags: project
status: active
github:
vercel:
folder: /root/projects/{{title}}
created: {{date}}
---

# {{title}}

## Beschrijving

> Wat is dit project en wat wil je ermee bereiken?

## Sessie beheer

```button
name 🔨 Nieuw project
type link
action https://n8n.jellespek.nl/webhook/new-project?name={{title}}
```

```button
name 🚀 Start sessie
type link
action https://n8n.jellespek.nl/webhook/start-project?session={{title}}&folder=/root/projects/{{title}}
```

```button
name 🛑 Stop sessie
type link
action https://n8n.jellespek.nl/webhook/stop-project?session={{title}}
```

```button
name ⚠️ Start (skip permissions)
type link
action https://n8n.jellespek.nl/webhook/start-project?session={{title}}&folder=/root/projects/{{title}}&mode=dangerous
```

## Links

- GitHub:
- Vercel:
- Docs:

## Notities

### Log

- {{date}} — Project aangemaakt
