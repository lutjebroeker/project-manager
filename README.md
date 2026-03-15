# Project Manager

Start, stop en maak Claude Code projecten vanuit Obsidian of de browser — zonder SSH.

**Live site:** https://project-manager-five-lemon.vercel.app
**Bedoeld domein:** https://projects.jellespek.nl *(Cloudflare + Vercel, nog in te stellen)*

---

## Hoe werkt het?

1. Open een project note in Obsidian (of de site)
2. Klik **🚀 Start sessie** → n8n start een tmux sessie + Claude Remote Control op de server
3. Browser redirect naar `claude.ai/code/...` — direct in je project

## Structuur

```
project-manager/
├── index.html                  # Project Manager site (deployed via Vercel)
├── vercel.json                 # Vercel routing config
├── workflow-manifest.json      # Versie-tracking voor n8n workflows
├── workflows/                  # n8n workflow exports
│   ├── O75vuWXjLj__start-project-session.json
│   ├── GfmBMQOHUdegYA1o__stop-project-session.json
│   └── YnOWKjbAUdJM7R9O__new-project-session.json
└── obsidian/
    └── Project Template.md     # Template voor Obsidian project notes
```

## n8n Workflows

| Workflow | Webhook | Functie |
|----------|---------|---------|
| Start Project Session | `/webhook/start-project?session=X&folder=Y` | Start/herstart tmux + Remote Control, redirect naar claude.ai |
| Stop Project Session | `/webhook/stop-project?session=X` | Kill tmux sessie + opruimen temp files |
| New Project Session | `/webhook/new-project?name=X` | GitHub repo aanmaken, clonen, sessie starten |

### Parameters Start Session

| Parameter | Verplicht | Beschrijving |
|-----------|-----------|--------------|
| `session` | ja | Naam van de tmux sessie (= project naam) |
| `folder` | ja | Absoluut pad op de server, bijv. `/root/projects/mijn-project` |
| `mode` | nee | `dangerous` voegt `--dangerously-skip-permissions` toe |

## Server

- **Host:** root@192.168.1.34
- **Projects root:** `/root/projects/{naam}`
- **Temp files:** `/tmp/claude-rc-{sessie}.txt`
- **Tmux windows:** `claude` / `shell` / `git`

## Obsidian instellen

1. Kopieer `obsidian/Project Template.md` naar `90. Templates/Project Template.md` in je vault
2. Maak een nieuwe note aan via de template (Templater of core Templates plugin)
3. De buttons werken direct via de Buttons plugin

## Site: nieuw project toevoegen

Voeg een object toe aan de `projects` array in `index.html`:

```js
{
  name: 'project-naam',        // ook de tmux sessie naam
  label: 'Leesbare naam',
  folder: '/root/projects/project-naam',
  github: 'https://github.com/lutjebroeker/project-naam',  // optioneel
  vercel: 'https://project.vercel.app',                    // optioneel
}
```

## Workflows importeren in n8n

1. Ga naar n8n → Workflows → Import
2. Upload het gewenste JSON bestand uit `/workflows/`
3. Controleer credentials (SSH Claude Code)
4. Voor `New Project Session`: vervang `{{GITHUB_PAT}}` door je echte GitHub token
5. Toggle workflow uit/aan om webhook te registreren

## Todo

- [ ] Cloudflare: CNAME `projects` → `cname.vercel-dns.com`
- [ ] Vercel: domein `projects.jellespek.nl` toevoegen
- [ ] Cloudflare Zero Trust Access instellen voor `projects.jellespek.nl`
- [ ] SSH Debug Test workflow verwijderen in n8n
- [ ] execution-engine en fit-journey migreren naar `/root/projects/` flat structuur (optioneel)
