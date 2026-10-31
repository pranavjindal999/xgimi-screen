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

  constructor() {
    super();
    this._built = false;
    this._boundKeyDown = (event) => this._onKeyDown(event);
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) {
      this._build();
      this._built = true;
    }
    this._update();
  }

  connectedCallback() {
    if (this._pad) {
      this._pad.addEventListener("keydown", this._boundKeyDown);
    }
  }

  disconnectedCallback() {
    if (this._pad) {
      this._pad.removeEventListener("keydown", this._boundKeyDown);
    }
  }

  getCardSize() {
    return 7;
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

  _build() {
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
        .remote {
          margin-top: 16px;
          padding-top: 12px;
          border-top: 1px solid var(--divider-color);
        }
        .remote-title {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 8px;
          margin-bottom: 10px;
        }
        .remote-title .hint { margin: 0; }
        .pad {
          outline: none;
          border-radius: 12px;
          padding: 4px;
        }
        .pad:focus {
          box-shadow: 0 0 0 2px var(--primary-color);
        }
        .pad-grid {
          display: grid;
          grid-template-columns: repeat(3, 56px);
          grid-template-rows: repeat(3, 56px);
          gap: 8px;
          justify-content: center;
        }
        .pad-nav {
          display: grid;
          grid-template-columns: repeat(2, 88px);
          gap: 8px;
          justify-content: center;
          margin-top: 8px;
        }
        .pad button {
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color, var(--card-background-color));
          color: var(--primary-text-color);
          border-radius: 12px;
          font-size: 18px;
          font-weight: 600;
          cursor: pointer;
        }
        .pad button:hover:not(:disabled) {
          border-color: var(--primary-color);
        }
        .pad button:active:not(:disabled) {
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
        }
        .pad button:disabled {
          opacity: 0.45;
          cursor: default;
        }
        .pad .up { grid-column: 2; grid-row: 1; }
        .pad .left { grid-column: 1; grid-row: 2; }
        .pad .ok { grid-column: 2; grid-row: 2; font-size: 14px; letter-spacing: 0.04em; }
        .pad .right { grid-column: 3; grid-row: 2; }
        .pad .down { grid-column: 2; grid-row: 3; }
        .pad .back, .pad .home { height: 44px; font-size: 13px; letter-spacing: 0.02em; }
      </style>
      <div class="body">
        <p class="missing" hidden>Edit this card and choose the projector Screen entity.</p>
        <div class="controls" hidden>
          <h2 class="title"></h2>
          <label class="row" data-kind="power">
            <span><span class="name">Power</span><span class="hint">Off is standby, not shutdown</span></span>
            <input type="checkbox" data-domain="switch">
          </label>
          <label class="row" data-kind="screen">
            <span><span class="name">Screen</span><span class="hint">Off blanks the image</span></span>
            <input type="checkbox" data-domain="switch">
          </label>
          <label class="slider" data-kind="brightness">
            <span class="name">Brightness</span>
            <span class="value">1</span>
            <input type="range" data-domain="number" min="1" max="10" step="1" value="1">
          </label>
          <label class="row" data-kind="boost">
            <span><span class="name">Luminance boost</span><span class="hint">Past level 10</span></span>
            <input type="checkbox" data-domain="switch">
          </label>
          <label class="slider" data-kind="volume">
            <span class="name">Volume</span>
            <span class="value">0</span>
            <input type="range" data-domain="number" min="0" max="100" step="1" value="0">
          </label>
          <div class="remote">
            <div class="remote-title">
              <span class="name">Remote</span>
              <span class="hint">Arrows, Return, Esc, Home</span>
            </div>
            <div class="pad" tabindex="0" aria-label="Projector remote">
              <div class="pad-grid">
                <button type="button" class="up" data-key="up" aria-label="Up">↑</button>
                <button type="button" class="left" data-key="left" aria-label="Left">←</button>
                <button type="button" class="ok" data-key="ok" aria-label="OK">OK</button>
                <button type="button" class="right" data-key="right" aria-label="Right">→</button>
                <button type="button" class="down" data-key="down" aria-label="Down">↓</button>
              </div>
              <div class="pad-nav">
                <button type="button" class="back" data-key="back" aria-label="Back">Back</button>
                <button type="button" class="home" data-key="home" aria-label="Home">Home</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    this.attachShadow({ mode: "open" });
    this.shadowRoot.append(this._card);

    this._missing = this.shadowRoot.querySelector(".missing");
    this._controls = this.shadowRoot.querySelector(".controls");
    this._title = this.shadowRoot.querySelector(".title");
    this._pad = this.shadowRoot.querySelector(".pad");
    this._fields = {
      power: this._bindToggle("power"),
      screen: this._bindToggle("screen"),
      brightness: this._bindSlider("brightness"),
      boost: this._bindToggle("boost"),
      volume: this._bindSlider("volume"),
    };

    this._pad.addEventListener("keydown", this._boundKeyDown);
    this._pad.querySelectorAll("button[data-key]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        this._sendKey(button.dataset.key);
        this._pad.focus();
      });
    });
  }

  _bindToggle(kind) {
    const row = this.shadowRoot.querySelector(`[data-kind="${kind}"]`);
    const input = row.querySelector("input");
    input.addEventListener("change", () => {
      if (!input.dataset.entity || !this._hass) {
        return;
      }
      this._hass.callService("switch", input.checked ? "turn_on" : "turn_off", {
        entity_id: input.dataset.entity,
      });
    });
    return { row, input };
  }

  _bindSlider(kind) {
    const row = this.shadowRoot.querySelector(`[data-kind="${kind}"]`);
    const input = row.querySelector("input");
    const value = row.querySelector(".value");
    input.addEventListener("input", () => {
      value.textContent = input.value;
    });
    input.addEventListener("change", () => {
      if (!input.dataset.entity || !this._hass) {
        return;
      }
      this._hass.callService("number", "set_value", {
        entity_id: input.dataset.entity,
        value: Number(input.value),
      });
    });
    return { row, input, value };
  }

  _update() {
    const hass = this._hass;
    const ids = this._entities();
    if (!ids.screen || !hass.states[ids.screen]) {
      this._missing.hidden = false;
      this._controls.hidden = true;
      return;
    }
    this._missing.hidden = true;
    this._controls.hidden = false;

    const screen = hass.states[ids.screen];
    const power = hass.states[ids.power];
    const brightness = hass.states[ids.brightness];
    const boost = hass.states[ids.boost];
    const volume = hass.states[ids.volume];
    this._title.textContent = (screen.attributes.friendly_name || "Projector").replace(
      / Screen$/,
      ""
    );
    const asleep = power && power.state === "off";

    this._setToggle(this._fields.power, power, false);
    this._setToggle(this._fields.screen, screen, asleep);
    this._setSlider(this._fields.brightness, brightness, asleep);
    this._setToggle(this._fields.boost, boost, asleep);
    this._setSlider(this._fields.volume, volume, asleep);

    this._pad.querySelectorAll("button").forEach((button) => {
      button.disabled = asleep || !screen || screen.state === "unavailable";
    });
    this._screenEntity = ids.screen;
  }

  _setToggle(field, entity, forceDisabled) {
    if (!entity) {
      field.row.hidden = true;
      return;
    }
    field.row.hidden = false;
    field.input.dataset.entity = entity.entity_id;
    const unavailable = entity.state === "unavailable" || entity.state === "unknown";
    if (this.shadowRoot.activeElement !== field.input) {
      field.input.checked = entity.state === "on";
    }
    field.input.disabled = unavailable || forceDisabled;
  }

  _setSlider(field, entity, forceDisabled) {
    if (!entity) {
      field.row.hidden = true;
      return;
    }
    field.row.hidden = false;
    field.input.dataset.entity = entity.entity_id;
    const max = entity.attributes.max ?? entity.attributes.maximum ?? 100;
    const min = entity.attributes.min ?? 0;
    field.input.min = min;
    field.input.max = max;
    const unavailable = entity.state === "unavailable" || entity.state === "unknown";
    if (this.shadowRoot.activeElement !== field.input) {
      const value = Number(entity.state);
      const shown = Number.isFinite(value) ? value : min;
      field.input.value = String(shown);
      field.value.textContent = String(shown);
    }
    field.input.disabled = unavailable || forceDisabled;
  }

  _onKeyDown(event) {
    const map = {
      ArrowUp: "up",
      ArrowDown: "down",
      ArrowLeft: "left",
      ArrowRight: "right",
      Enter: "ok",
      NumpadEnter: "ok",
      Escape: "back",
      Backspace: "back",
      Home: "home",
    };
    const key = map[event.key];
    if (!key) {
      return;
    }
    // Enter on a focused D-pad button already activates that button.
    if (
      (event.key === "Enter" || event.key === "NumpadEnter") &&
      event.target.closest("button[data-key]")
    ) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    this._sendKey(key);
  }

  _sendKey(key) {
    if (!this._hass || !this._screenEntity) {
      return;
    }
    const button = this._pad.querySelector(`button[data-key="${key}"]`);
    if (button && button.disabled) {
      return;
    }
    this._hass.callService("xgimi_screen", "send_key", {
      entity_id: this._screenEntity,
      key,
    });
  }
}

class XgimiScreenCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...(config || {}) };
    if (this._picker) {
      this._picker.value = this._config.screen || "";
    }
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
        this._config = { ...(this._config || {}), screen: event.detail.value };
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
    this._picker.value = (this._config && this._config.screen) || "";
  }
}

if (!customElements.get("xgimi-screen-card")) {
  customElements.define("xgimi-screen-card", XgimiScreenCard);
}
if (!customElements.get("xgimi-screen-card-editor")) {
  customElements.define("xgimi-screen-card-editor", XgimiScreenCardEditor);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "xgimi-screen-card")) {
  window.customCards.push({
    type: "xgimi-screen-card",
    name: "XGIMI Screen",
    description:
      "Power, screen, brightness, luminance boost, volume, and a D-pad remote on one card.",
  });
}
