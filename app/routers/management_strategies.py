"""
Management Strategies API Router
Provides pest management recommendations per pest type.
Source: Nature Damage of Coconut Pests – PDF (PCA Reference)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/management-strategies", tags=["management-strategies"])

MANAGEMENT_STRATEGIES = {
    "Rhinoceros Beetle": {
        "pest_name": "Oryctes rhinoceros (Rhinoceros Beetle)",
        "scientific_name": "Oryctes rhinoceros",
        "reference_pages": "Pages 3–23",
        "strategies": [
            {
                "category": "Cultural Control",
                "icon": "🌱",
                "items": [
                    "Maintain strict farm sanitation by removing decomposing organic matter such as rotting logs, manure heaps, and decaying plant residues that serve as breeding sites.",
                    "Practice intercropping and cover cropping to reduce exposed breeding areas.",
                    "Apply proper fertilization to help palms recover from crown damage and improve tolerance.",
                ],
            },
            {
                "category": "Mechanical / Physical Control",
                "icon": "🔧",
                "items": [
                    "Manually extract adult beetles from the crown, especially in young palms.",
                    "Apply coal tar or similar protective materials on wounds to prevent further beetle entry.",
                    "Use log traps placed around the farm to attract and destroy adult beetles.",
                ],
            },
            {
                "category": "Biological Control",
                "icon": "🦠",
                "items": [
                    "Apply green muscardine fungus (Metarhizium anisopliae) in breeding sites.",
                    "Use Oryctes nudivirus (OrNV) through infected beetle release or treated traps to suppress populations.",
                ],
            },
            {
                "category": "Chemical Control",
                "icon": "⚗️",
                "items": [
                    "Use systemic insecticide trunk or frond injection when infestation is severe.",
                    "Conduct soil drenching or root infusion where recommended.",
                    "Deploy aggregation pheromone traps as part of mass trapping programs.",
                ],
            },
        ],
    },
    "Brontispa": {
        "pest_name": "Brontispa longissima (Coconut Leaf Beetle)",
        "scientific_name": "Brontispa longissima",
        "reference_pages": "Pages 28–37",
        "strategies": [
            {
                "category": "Cultural Control",
                "icon": "🌱",
                "items": [
                    "Remove and destroy infested spear leaves immediately to stop population buildup.",
                    "Ensure proper fertilization to promote faster recovery and leaf regeneration.",
                    "Observe quarantine measures to prevent spread between farms.",
                ],
            },
            {
                "category": "Mechanical / Physical Control",
                "icon": "🔧",
                "items": [
                    "Manually cut and dispose of heavily infested folded leaves.",
                    "Avoid leaving removed leaves in the plantation to prevent reinfestation.",
                ],
            },
            {
                "category": "Biological Control",
                "icon": "🦠",
                "items": [
                    "Release parasitoid wasp (Tetrastichus brontispae), a primary biological control agent.",
                    "Encourage predators such as earwig (Chelisoches morio).",
                    "Spray entomopathogenic fungi (Beauveria bassiana or Metarhizium anisopliae) directly on the spear leaf only until drip.",
                ],
            },
            {
                "category": "Chemical Control",
                "icon": "⚗️",
                "items": [
                    "Chemical use is generally discouraged in favor of biological control.",
                    "Consult PCA for approved chemical treatments if biological control is insufficient.",
                ],
            },
        ],
    },
    "APW": {
        "pest_name": "Asiatic Palm Weevil (APW)",
        "scientific_name": "Rhynchophorus ferrugineus",
        "reference_pages": "Pages 96–110",
        "strategies": [
            {
                "category": "Cultural Control",
                "icon": "🌱",
                "items": [
                    "Practice strict sanitation by removing and destroying severely infested palms.",
                    "Avoid trunk injuries during harvesting, pruning, or farm operations.",
                    "Apply preventive trunk spraying to discourage egg laying.",
                    "Enforce quarantine regulations to prevent pest spread.",
                ],
            },
            {
                "category": "Mechanical / Physical Control",
                "icon": "🔧",
                "items": [
                    "Conduct regular surveillance for holes, frass, fermented odor, and gnawing sounds.",
                    "Cut and destroy palms with extensive internal damage.",
                ],
            },
            {
                "category": "Biological Control",
                "icon": "🦠",
                "items": [
                    "Apply entomopathogenic fungus (Beauveria bassiana).",
                    "Use nematode (Praecocilenchus ferruginophorus) against larvae.",
                    "Utilize natural enemies such as Pseudomonas aeruginosa, predatory mites (Hypoaspis spp.), and earwigs (Chelisoches morio).",
                ],
            },
            {
                "category": "Chemical Control",
                "icon": "⚗️",
                "items": [
                    "Apply the Drill–Pour–Plug Method: Drill holes into the trunk, pour insecticide solution, then seal holes to retain chemical.",
                    "Consult PCA for exact insecticide name, dosage, and pre-harvest interval (PHI).",
                ],
            },
        ],
    },
    "Slug Caterpillar": {
        "pest_name": "Slug Caterpillar",
        "scientific_name": "Parasa lepida",
        "reference_pages": "Pages 123–129",
        "strategies": [
            {
                "category": "Cultural Control",
                "icon": "🌱",
                "items": [
                    "Conduct leaf pruning following PCA-recommended procedures only to reduce larval population.",
                    "Focus on young palms and seedlings where damage is more severe.",
                ],
            },
            {
                "category": "Mechanical / Physical Control",
                "icon": "🔧",
                "items": [
                    "Collect and destroy pupal cocoons found on leaves or trunks.",
                    "Use light traps to attract and kill adult moths.",
                ],
            },
            {
                "category": "Biological Control",
                "icon": "🦠",
                "items": [
                    "Release hymenopterous parasitoids.",
                    "Apply fungal pathogens and nuclear polyhedrosis virus (NPV).",
                    "Spray virus-water suspension prepared from virus-infected larvae, especially on seedlings.",
                ],
            },
            {
                "category": "Chemical Control",
                "icon": "⚗️",
                "items": [
                    "Consult PCA for approved chemical treatments when biological control is insufficient.",
                    "Chemical information not specified in the reference document.",
                ],
            },
        ],
    },
    "White Grub": {
        "pest_name": "White Grub",
        "scientific_name": "Leucopholis irrorata",
        "reference_pages": "",
        "strategies": [
            {
                "category": "Cultural Control",
                "icon": "🌱",
                "items": [
                    "Remove decaying organic materials around the plantation.",
                    "Practice crop rotation and proper land preparation.",
                ],
            },
            {
                "category": "Mechanical / Physical Control",
                "icon": "🔧",
                "items": [
                    "Hand-collect grubs during land preparation.",
                    "Use light traps to capture adult beetles.",
                ],
            },
            {
                "category": "Biological Control",
                "icon": "🦠",
                "items": [
                    "Apply entomopathogenic fungi (Metarhizium anisopliae) to soil.",
                    "Use entomopathogenic nematodes for soil treatment.",
                ],
            },
            {
                "category": "Chemical Control",
                "icon": "⚗️",
                "items": [
                    "Apply soil-applied insecticides as recommended by PCA.",
                    "Conduct soil drenching around affected root zones.",
                ],
            },
        ],
    },
}

# Aliases for pests that have multiple detection labels
PEST_ALIASES = {
    "APW Adult": "APW",
    "APW Larvae": "APW",
    "Brontispa Pupa": "Brontispa",
    "Oryctes rhinoceros": "Rhinoceros Beetle",
    "Rhynchophorus ferrugineus": "APW",
    "Brontispa longissima": "Brontispa",
    "Parasa lepida": "Slug Caterpillar",
    "Leucopholis irrorata": "White Grub",
}


def _resolve_pest(pest_name: str) -> str:
    """Resolve pest aliases to canonical name."""
    if pest_name in MANAGEMENT_STRATEGIES:
        return pest_name
    if pest_name in PEST_ALIASES:
        return PEST_ALIASES[pest_name]
    # Fuzzy match
    lower = pest_name.lower()
    for key in MANAGEMENT_STRATEGIES:
        if key.lower() in lower or lower in key.lower():
            return key
    for alias, canonical in PEST_ALIASES.items():
        if alias.lower() in lower or lower in alias.lower():
            return canonical
    return pest_name


@router.get("")
def list_all_strategies():
    """Get all management strategies for all pests."""
    return {
        "pests": list(MANAGEMENT_STRATEGIES.keys()),
        "strategies": MANAGEMENT_STRATEGIES,
    }


@router.get("/{pest_name}")
def get_strategies_for_pest(pest_name: str):
    """Get management strategies for a specific pest."""
    resolved = _resolve_pest(pest_name)
    if resolved not in MANAGEMENT_STRATEGIES:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"No management strategies found for '{pest_name}'. Available pests: {list(MANAGEMENT_STRATEGIES.keys())}",
        )
    return {
        "pest_key": resolved,
        **MANAGEMENT_STRATEGIES[resolved],
    }
