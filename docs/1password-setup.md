# 1Password — HA Token Setup

Never hardcode the HA token. Use 1Password CLI to inject it at runtime.

## 1. Store the token in 1Password

1. Open 1Password → create item under **HomeServer** vault
2. Title: `Home Assistant`
3. Fields:
   - `url` → `http://YOUR_HA_IP:8123` (or Tailscale URL)
   - `credential` → your HA long-lived access token

## 2. Install the op CLI

```bash
# NixOS
environment.systemPackages = [ pkgs._1password ];

# Or via nixos-dotfiles
```

Sign in once:
```bash
op signin
```

## 3. Run scripts with token injected

Create a `.env.tpl` file (already gitignored):
```bash
HA_TOKEN=op://HomeServer/Home Assistant/credential
HA_URL=op://HomeServer/Home Assistant/url
```

Run any script:
```bash
op run --env-file=.env.tpl -- python scripts/morning_blinds_forecast.py
```

## 4. One-liner for quick API calls

```bash
curl -s \
  -H "Authorization: Bearer $(op read 'op://HomeServer/Home Assistant/credential')" \
  "$(op read 'op://HomeServer/Home Assistant/url')/api/states/input_select.house_mode"
```

## 5. deploy.sh

```bash
op run --env-file=.env.tpl -- ./scripts/deploy.sh
```

## Reminder

- Never paste the real token into AI chats, Slack, or anywhere — use `op read` instead
- If you suspect a token was exposed: delete it in HA (Profile → Security → Long-lived tokens), generate a new one, update 1Password
