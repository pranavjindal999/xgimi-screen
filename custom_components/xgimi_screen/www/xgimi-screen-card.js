class XgimiScreenCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("xgimi-screen-card-editor");
  }

  static getStubConfig(hass) {
    const screen = Object.keys(hass.states).find(
      (entityId) => entityId.startsWith("switch.") && entityId.endsWith("_screen")
    );
    return screen ? { screen } : {};
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._card) {
      this._card = document.createElement("ha-card");
      this._card.innerHTML = `
        <style>
          .body { padding: 16px 16px 12px; }
          .title { font-size: 16px; font-weight: 500; margin: 0 0 12px; }
          .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 40px; }
          .name { display: block; }
          .hint { display: block; color: var(--secondary-text-color); font-size: 12px; }
          .slider { display: grid; grid-template-columns: 1fr auto; gap: 8px 12px; align-items: center; margin: 8px 0; }
          .slider input { width: 100%; accent-color: var(--primary-color); }
          .value { min-width: 2ch; text-align: right; font-variant-numeric: tabular-nums; }
          input[type="checkbox"] { width: 40px; height: 22px; accent-color: var(--primary-color); }
          .missing { color: var(--secondary-text-color); }
        </style>
        <div class="body"></div>
      `;
      this.attachShadow({ mode: "open" });
      this.shadowRoot.append(this._card);
    }
    this._render();
  }

  getCardSize() {
    return 5;
  }

  _entities() {
    const config = this._config || {};
    const screen = config.screen;
    if (!screen || !screen.endsWith("_screen")) {
      return { screen };
    }
    const stem = screen.slice(0, -"_screen".length).split(".")[1];
    const derived = (domain, suffix) => `${domain}.${stem}_${suffix}`;
    return {
      screen,
      power: config.power || derived("switch", "power"),
      brightness: config.brightness || derived("number", "brightness"),
      boost: config.boost || derived("switch", "luminance_boost"),
      volume: config.volume || derived("number", "volume"),
    };
  }

  _render() {
    const body = this.shadowRoot.querySelector(".body");
    const hass = this._hass;
    const ids = this._entities();
    if (!ids.screen || !hass.states[ids.screen]) {
      body.innerHTML = `<p class="missing">Edit this card and choose the projector Screen entity.</p>`;
      return;
    }
    const screen = hass.states[ids.screen];
    const power = hass.states[ids.power];
    const brightness = hass.states[ids.brightness];
    const boost = hass.states[ids.boost];
    const volume = hass.states[ids.volume];
    const title = (screen.attributes.friendly_name || "Projector").replace(/ Screen$/, "");
    const asleep = power && power.state === "off";
    const row = (label, hint, entity, kind) => {
      if (!entity) {
        return "";
      }
      const unavailable = entity.state === "unavailable" || entity.state === "unknown";
      const disabled = unavailable || (asleep && kind !== "power");
      if (kind === "toggle" || kind === "power") {
        const checked = entity.state === "on" ? "checked" : "";
        return `<label class="row">
          <span><span class="name">${label}</span>${hint ? `<span class="hint">${hint}</span>` : ""}</span>
          <input type="checkbox" data-entity="${entity.entity_id}" data-domain="switch" ${checked} ${disabled ? "disabled" : ""}>
        </label>`;
      }
      const max = entity.attributes.max ?? entity.attributes.maximum ?? 100;
      const min = entity.attributes.min ?? 0;
      const value = Number(entity.state);
      const shown = Number.isFinite(value) ? value : min;
      return `<label class="slider">
        <span class="name">${label}</span>
        <span class="value">${shown}</span>
        <input type="range" data-entity="${entity.entity_id}" data-domain="number" min="${min}" max="${max}" step="1" value="${shown}" ${disabled ? "disabled" : ""}>
      </label>`;
    };
    body.innerHTML = `
      <h2 class="title">${title}</h2>
      ${row("Power", "Off is standby, not shutdown", power, "power")}
      ${row("Screen", "Off blanks the image", screen, "toggle")}
      ${row("Brightness", "", brightness, "slider")}
      ${row("Luminance boost", "Past level 10", boost, "toggle")}
      ${row("Volume", "", volume, "slider")}
    `;
    body.querySelectorAll("input[type=checkbox]").forEach((input) => {
      input.addEventListener("change", () => {
        hass.callService("switch", input.checked ? "turn_on" : "turn_off", {
          entity_id: input.dataset.entity,
        });
      });
    });
    body.querySelectorAll("input[type=range]").forEach((input) => {
      input.addEventListener("input", () => {
        input.parentElement.querySelector(".value").textContent = input.value;
      });
      input.addEventListener("change", () => {
        hass.callService("number", "set_value", {
          entity_id: input.dataset.entity,
          value: Number(input.value),
        });
      });
    });
  }
}

class XgimiScreenCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._picker) {
      this._picker = document.createElement("ha-entity-picker");
      this._picker.includeDomains = ["switch"];
      this._picker.label = "Screen entity";
      this._picker.style.display = "block";
      this._picker.style.padding = "16px";
      this._picker.addEventListener("value-changed", (event) => {
        this._config = { ...this._config, screen: event.detail.value };
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: this._config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.append(this._picker);
    }
    this._picker.hass = hass;
    this._picker.value = this._config.screen || "";
  }
}

customElements.define("xgimi-screen-card", XgimiScreenCard);
customElements.define("xgimi-screen-card-editor", XgimiScreenCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "xgimi-screen-card",
  name: "XGIMI Screen",
  description: "Power, screen, brightness, luminance boost, and volume on one card.",
});
