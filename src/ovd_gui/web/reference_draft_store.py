import uuid
from collections import OrderedDict
from typing import ClassVar

from PIL import Image

from .reference_draft import ReferenceDraft


class ReferenceDraftStore:
    """
    Reference images opened for boxing, kept until they are added to a class or pushed out by newer ones.
    """

    CAPACITY: ClassVar[int] = 16

    def __init__(self) -> None:
        self._drafts: OrderedDict[str, ReferenceDraft] = OrderedDict()

    def add(self, name: str, image: Image.Image) -> ReferenceDraft:
        """
        Keep a reference image for boxing.

        Parameters
        ----------
        name : str
            Display name of the image.
        image : Image.Image
            EXIF-upright RGB pixels.

        Returns
        -------
        ReferenceDraft
            Draft with a new identifier.
        """
        draft: ReferenceDraft = ReferenceDraft(draft_id=uuid.uuid4().hex, name=name, image=image)
        self._drafts[draft.draft_id] = draft
        while len(self._drafts) > self.CAPACITY:
            self._drafts.popitem(last=False)
        return draft

    def get(self, draft_id: str) -> ReferenceDraft:
        """
        Draft kept under an identifier.

        Parameters
        ----------
        draft_id : str
            Identifier of the draft.

        Returns
        -------
        ReferenceDraft
            Kept draft.

        Raises
        ------
        KeyError
            If no draft has the identifier any more.
        """
        if draft_id not in self._drafts:
            raise KeyError("The reference image is no longer open; add it again.")
        return self._drafts[draft_id]

    def discard(self, draft_id: str) -> None:
        """
        Forget a draft.

        Parameters
        ----------
        draft_id : str
            Identifier of the draft; nothing happens if it is unknown.
        """
        self._drafts.pop(draft_id, None)
