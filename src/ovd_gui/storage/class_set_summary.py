from dataclasses import dataclass


@dataclass(frozen=True)
class ClassSetSummary:
    """
    Counts describing a class set, read from its manifest without decoding any image.

    Attributes
    ----------
    class_names : tuple[str, ...]
        Class names in class id order.
    phrase_count : int
        Number of text prompts over all classes.
    reference_image_count : int
        Number of distinct reference images.
    """

    class_names: tuple[str, ...]
    phrase_count: int
    reference_image_count: int

    @property
    def description(self) -> str:
        """
        One-line description of the counts.

        Returns
        -------
        str
            E.g. ``"3 classes · 5 text prompts · 2 images"``; zero counts of prompts and images are left out.
        """
        parts: list[str] = [self._count_of(len(self.class_names), "class", "classes")]
        if self.phrase_count:
            parts.append(self._count_of(self.phrase_count, "text prompt", "text prompts"))
        if self.reference_image_count:
            parts.append(self._count_of(self.reference_image_count, "image", "images"))
        return " · ".join(parts)

    @staticmethod
    def _count_of(count: int, singular: str, plural: str) -> str:
        return f"{count} {singular if count == 1 else plural}"
