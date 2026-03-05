from appai.models.deck_build import DeckBuildStatus

POLLABLE_BUILD_STATUSES: tuple[str, ...] = (
    str(DeckBuildStatus.PENDING),
    str(DeckBuildStatus.IN_PROGRESS),
    str(DeckBuildStatus.BUILDING_DECK),
    str(DeckBuildStatus.CLASSIFYING_DECK_CARDS),
    str(DeckBuildStatus.FINDING_REPLACEMENT_CARDS),
)


def is_pollable_build_status(status: str) -> bool:
    """Return whether a deck build status is pollable (actively in progress).

    Args:
        status (str): The deck build status value to evaluate.

    Returns:
        bool: True if the status is in the pollable in-progress set; otherwise False.
    """
    return status in POLLABLE_BUILD_STATUSES
