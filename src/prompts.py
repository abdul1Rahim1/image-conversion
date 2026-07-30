"""Prompt library for image edits and copy rewrites."""

VARIATION_PROMPTS = [
    (
        "This is a product catalog image. Create another authentic professional "
        "studio photograph of the EXACT SAME product. Preserve the product's "
        "identity, branding, logo, colors, shape, material, packaging, and "
        "labels with absolute fidelity. Change ONLY: camera angle (three-"
        "quarter view), lighting (softer key light from the left), shadows, "
        "and a clean neutral seamless background. Output must look like a "
        "real studio shot of the same physical product — no drawing, no "
        "illustration, no stylization."
    ),
    (
        "Reshoot this exact product from a different perspective. Keep every "
        "visible detail — brand, logo, model, colors, materials, dimensions, "
        "packaging, labels — pixel-faithful to the original. Change ONLY: "
        "perspective (slight top-down), lighting (warm diffused overhead), "
        "surface reflections, depth of field (shallow focus on the label), "
        "and a subtle contextual surface (light wood or matte white). "
        "Photorealistic studio quality only."
    ),
    (
        "Produce another professional e-commerce photograph of the SAME "
        "product shown. Do not alter brand, logo, colors, shape, or any "
        "printed text. Change ONLY: camera angle (front-facing straight on), "
        "lighting (bright even softbox), background (pure white infinity "
        "cove), and eliminate hard shadows. Must be indistinguishable from "
        "a real catalog photograph of this exact SKU."
    ),
    (
        "Create another realistic product photo of this exact item. Preserve "
        "all identifying features — brand marks, colors, textures, form. "
        "Change ONLY: angle (side profile), a moody low-key lighting setup "
        "with a single rim light, dark gradient background, and glossy "
        "reflection on the surface below. Photograph must remain a "
        "faithful representation of the actual product."
    ),
]


REWRITE_SYSTEM = (
    "You rewrite e-commerce product copy. You preserve every factual claim "
    "(brand, model, materials, dimensions, capacity, quantity, compatibility, "
    "certifications) with 100% fidelity. You never invent specs. You produce "
    "fresh wording — different sentence structure, different word choices, "
    "different order — so the result would not match the original under "
    "text-similarity checks, while conveying the same meaning to a shopper."
)


def rewrite_user_prompt(title: str, description: str) -> str:
    return (
        "Rewrite the product title and description below.\n\n"
        "Return valid JSON with exactly two keys: \"title\" and "
        "\"description\". No prose, no markdown, no code fences.\n\n"
        f"ORIGINAL TITLE:\n{title}\n\n"
        f"ORIGINAL DESCRIPTION:\n{description}\n"
    )
