# Contributing to Home Assistant Helium Hotspot Integration

🎉 First off, thanks for considering contributing! This project exists to make it easy to monitor **Helium Mobile hotspots** from within Home Assistant. Contributions are welcome in many forms — code, documentation, bug reports, or feature requests.

---

## 🐛 Reporting Issues

* Use the [Issues tab](../../issues) to file a bug.
* Include:

  * Your Home Assistant version (`Settings → About`).
  * Integration version (`manifest.json` version or HACS release tag).
  * Hotspot ID(s) you’re monitoring.
  * Relevant logs (enable debug, see below).

Enable debug logging in `configuration.yaml` to capture parser/coordinator output:

```yaml
logger:
  default: warning
  logs:
    custom_components.helium_hotspot: debug
```

---

## 💡 Requesting Features

* Open a [Feature Request issue](../../issues).
* Be clear about the **problem you want to solve** (not just a solution).
* Include screenshots or examples from [world.helium.com](https://world.helium.com) if relevant.

---

## 🛠️ Development Setup

1. Fork & clone this repository:

   ```bash
   git clone https://github.com/<youruser>/home-assistant-helium-hotspot.git
   cd home-assistant-helium-hotspot
   ```

2. Set up a dev environment with Home Assistant Core or [Devcontainer](https://developers.home-assistant.io/docs/devcontainer).

3. Symlink the integration into HA config:

   ```bash
   ln -s $(pwd)/custom_components/helium_hotspot ~/.homeassistant/custom_components/helium_hotspot
   ```

4. Restart Home Assistant.

---

## 📦 Making Changes

* Follow the [Home Assistant developer docs](https://developers.home-assistant.io/).
* Keep code formatted with `black` and linted with `flake8`.
* Run `hassfest` and `hacs` validators locally or via GitHub Actions.

---

## 🔄 Submitting Pull Requests

1. Create a feature branch:

   ```bash
   git checkout -b feature/my-improvement
   ```
2. Commit changes with clear messages.
3. Push to your fork and open a Pull Request.
4. Ensure all CI checks (hassfest + hacs) pass.

---

## 🌍 Translations

* All user-facing strings live in `custom_components/helium_hotspot/translations/`.
* Default is `en.json`. Add other languages as `{lang}.json`.

---

## 🖼️ Docs & Screenshots

* Place screenshots in `docs/screenshots/` and reference them in `README.md`.
* Keep images small, PNG or GIF, and optimized for dark/light themes.

---

## 📜 License

By contributing, you agree that your code/documentation contributions will be licensed under the [MIT License](LICENSE).