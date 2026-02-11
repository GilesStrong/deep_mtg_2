EXTRACTION_SCHEMA: str = """
.data.cards[] | {
    colors: .colors,
    convertedManaCost: .convertedManaCost,
    keywords: .keywords,
    manaCost: .manaCost,
    name: .name,
    power: .power,
    rarity: .rarity,
    subtypes: .subtypes,
    supertypes: .supertypes,
    text: .text,
    toughness: .toughness,
    types: .types,
    setCode: .setCode
}
"""
