"""Step 4 — Claude API call to generate a structured desk narrative."""

import json
import datetime

import anthropic

import config


def _rule_based_narrative(metrics_dict: dict) -> str:
    """Generate a structured desk note from metrics using templates."""
    m = {k: v[0] for k, v in metrics_dict.items()}

    # Gas tightness
    z = m["TTF 30d Z-Score"]
    stor = m["Storage vs 5yr Avg"]
    if z > 1:
        gas_tone = f"Gas is tight. TTF z-score at {z:+.2f} puts price well above its 30-day mean."
    elif z > 0.3:
        gas_tone = f"Gas is moderately firm. TTF z-score at {z:+.2f} sits above the 30-day mean."
    elif z < -1:
        gas_tone = f"Gas is loose. TTF z-score at {z:+.2f} indicates price well below its 30-day mean."
    elif z < -0.3:
        gas_tone = f"Gas is soft. TTF z-score at {z:+.2f} sits below the 30-day mean."
    else:
        gas_tone = f"Gas is range-bound. TTF z-score at {z:+.2f} is near the 30-day mean."

    if stor < -10:
        stor_tone = f"Storage is {stor:+.1f}pp below the 5-year seasonal average — a material deficit that supports winter risk premium."
    elif stor < 0:
        stor_tone = f"Storage runs {stor:+.1f}pp below the 5-year average, a mild deficit."
    elif stor > 10:
        stor_tone = f"Storage is {stor:+.1f}pp above the 5-year average — ample cushion dampens winter risk."
    else:
        stor_tone = f"Storage at {stor:+.1f}pp vs the 5-year average is broadly in line with seasonal norms."

    # Carbon signal
    eua_ratio = m["EUA/TTF Ratio"]
    if eua_ratio > 1.5:
        carbon_tone = f"Carbon dominates. EUA/TTF ratio at {eua_ratio:.2f} means carbon cost is the primary marginal cost driver, widening the gap between coal and gas SRMC."
    elif eua_ratio > 1.0:
        carbon_tone = f"Carbon is a significant factor. EUA/TTF ratio at {eua_ratio:.2f} adds meaningful cost pressure to coal-fired generation."
    else:
        carbon_tone = f"Carbon is secondary. EUA/TTF ratio at {eua_ratio:.2f} means gas cost dominates the marginal cost stack."

    # Power curve
    cds = m["Clean Dark Spread"]
    css = m["Clean Spark Spread"]
    srmc = m["Implied SRMC (marginal)"]
    if css > cds and css > 0:
        margin_unit = "gas"
        power_tone = f"Gas is at the margin with CSS at {css:+.1f} EUR/MWh vs CDS at {cds:+.1f}. Power tracks TTF + EUA."
    elif cds > css and cds > 0:
        margin_unit = "coal"
        power_tone = f"Coal is at the margin with CDS at {cds:+.1f} EUR/MWh vs CSS at {css:+.1f}. Power tracks coal + carbon."
    else:
        margin_unit = "gas" if css > cds else "coal"
        power_tone = f"Both spreads are negative (CDS {cds:+.1f}, CSS {css:+.1f} EUR/MWh) — generation is unprofitable at current prices."
    power_tone += f" Implied marginal SRMC is {srmc:.1f} EUR/MWh."

    if cds < -20:
        direction = "The deeply negative dark spread suggests Cal+1 baseload has downside risk if gas eases further."
    elif cds > 5:
        direction = "Positive dark spread supports Cal+1 baseload at current levels."
    else:
        direction = "Near-zero dark spread points to a balanced Cal+1 baseload outlook."

    # Key risk
    if stor < -15 and z < -0.5:
        risk = f"Key risk: gas is priced loose despite a {stor:+.1f}pp storage deficit — any supply disruption or cold snap reprices TTF sharply higher, dragging power and carbon with it."
    elif z > 1.5:
        risk = f"Key risk: TTF z-score at {z:+.2f} is stretched — a demand-side disappointment or LNG cargo arrival could trigger a sharp pullback in gas and power."
    elif stor > 10:
        risk = f"Key risk: surplus storage at {stor:+.1f}pp above seasonal norms caps upside — a mild winter forecast could push gas and power materially lower."
    else:
        risk = f"Key risk: with storage at {stor:+.1f}pp vs average and z-score at {z:+.2f}, the main threat is a geopolitical supply disruption that reprices the entire complex higher."

    return f"""**1. Gas tightness**
{gas_tone} {stor_tone}

**2. Carbon signal**
{carbon_tone}

**3. Power curve implications**
{power_tone} {direction}

**4. Key risk**
{risk}"""


def generate_narrative(metrics_dict: dict, chart_paths: list) -> str:
    """
    Build a structured prompt from today's metric values.
    Call claude-sonnet-4-20250514.
    Return the narrative string.
    Log prompt + response to JSONL.
    """
    api_key = config.ANTHROPIC_API_KEY or None
    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    # --- Build the metrics block ---
    metrics_text = "\n".join([
        f"- {name}: {vals[0]:.2f}"
        for name, vals in metrics_dict.items()
    ])

    system_prompt = (
        "You are a senior European power and gas trader writing "
        "a morning desk note. You are precise, direct, and quantitative. You do not "
        "pad with caveats. You write in present tense. You never say 'it is important "
        "to note'. You always anchor observations to specific numbers."
    )

    user_prompt = f"""Today's cross-commodity metrics ({datetime.date.today()}):

{metrics_text}

Write a desk note with the following sections:
1. **Gas tightness** (3–5 sentences): interpret the TTF z-score and storage
   deficit/surplus. Is gas tight or loose? What does this imply for winter
   risk premium?
2. **Carbon signal** (2–4 sentences): interpret the EUA level and EUA/TTF
   ratio. Is carbon adding to or subtracting from marginal cost pressure?
3. **Power curve implications** (4–6 sentences): given the CDS, CSS, and
   SRMC, which fuel is at the margin? Is the dark spread positive or
   negative — what does this say about Cal+1 baseload direction?
4. **Key risk** (1–2 sentences): state the single biggest risk to the
   current view (upside or downside).

Keep total length under 350 words. Use numbers throughout."""

    # --- Try Anthropic Claude API ---
    if client is not None:
        try:
            model_used = "claude-sonnet-4-20250514"
            response = client.messages.create(
                model=model_used,
                max_tokens=600,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
            )
            narrative = response.content[0].text
            _log(model_used, system_prompt, user_prompt, narrative,
                 response.usage.input_tokens, response.usage.output_tokens)
            print(f"  Narrative generated via Claude ({response.usage.output_tokens} tokens)")
            return narrative
        except Exception as e:
            import warnings
            warnings.warn(f"Claude API failed ({e}); trying Gemini…")

    # --- Try Google Gemini API ---
    gemini_key = config.GEMINI_API_KEY or None
    if gemini_key:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=gemini_key)
            model_used = "gemini-2.0-flash"
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = gemini_client.models.generate_content(
                model=model_used,
                contents=full_prompt,
            )
            narrative = response.text
            in_tok = response.usage_metadata.prompt_token_count or 0
            out_tok = response.usage_metadata.candidates_token_count or 0
            _log(model_used, system_prompt, user_prompt, narrative, in_tok, out_tok)
            print(f"  Narrative generated via Gemini ({out_tok} tokens)")
            return narrative
        except Exception as e:
            import warnings
            warnings.warn(f"Gemini API failed ({e}); falling back to rule-based narrative.")

    # --- Rule-based fallback ---
    narrative = _rule_based_narrative(metrics_dict)
    _log("rule-based-fallback", system_prompt, user_prompt, narrative, 0, 0)
    print("  Using rule-based narrative (no API key or API error)")
    return narrative


def _log(model, system_prompt, user_prompt, narrative, in_tokens, out_tokens):
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "model": model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": narrative,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
    }
    log_path = config.LOGS_DIR / "prompt_log.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    print(f"  Logged to {log_path}")
