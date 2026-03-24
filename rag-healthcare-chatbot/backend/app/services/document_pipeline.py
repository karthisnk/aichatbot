import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path

import fitz

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency
    Image = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

from app.config import PROCESSED_DATA_DIR, SUPPORTED_DOMAINS, TESSERACT_CMD


DOMAIN_KEYWORDS = {
    "patient": (
        "patient",
        "profile",
        "demographic",
        "clinical",
        "visit",
        "history",
        "registration",
        "insurance",
        "admission",
    ),
    "prescription": (
        "prescription",
        "medication",
        "medicine",
        "dose",
        "dosage",
        "drug",
        "pharmacy",
        "refill",
        "rx",
    ),
    "alerts": (
        "alert",
        "warning",
        "critical",
        "notification",
        "risk",
        "attention",
        "contraindication",
        "caution",
    ),
    "troubleshooting": (
        "troubleshooting",
        "error",
        "issue",
        "problem",
        "resolve",
        "resolution",
        "faq",
        "support",
        "fix",
    ),
}

MIN_SECTION_TEXT_CHARS = 120
MERGE_TARGET_CHARS = 900
MAX_SECTION_TEXT_CHARS = 1500
MAX_MULTIMODAL_TEXT_CHARS = 2200
MIN_IMAGE_ONLY_TITLE_CHARS = 12
MIN_IMAGE_BYTES = 2048
MIN_IMAGE_DIMENSION = 96
MAX_DUPLICATE_IMAGE_REUSE = 2

NOISE_TITLE_PATTERNS = (
    r"^figure\s+\d",
    r"^table of contents$",
    r"^contents$",
    r"^[ivxlcdm]+$",
    r"^page \d+$",
    r"^chapter \d+\s*$",
    r"^end of chapter$",
    r"^.*\s\d+$",
    r"^warning$",
    r"^caution$",
)
NOISE_TEXT_PATTERNS = (
    r"^\s*(?:\u2022|-)\s*$",
    r"^p/n:",
    r"^for more information, contact",
)
STEP_LINE_PATTERN = re.compile(
    r"^\s*(?:step\s+\d+[:.)-]?|\d+[\).]|(?:\u2022|-|\*))\s+\S+",
    flags=re.IGNORECASE,
)
TOC_LINE_PATTERN = re.compile(r"\.{3,}\s*[a-z0-9-]*\d+\s*$", flags=re.IGNORECASE)
LEGAL_TEXT_PATTERN = re.compile(
    r"(all rights reserved|proprietary information|may not be disclosed|written permission|trademarks? are the property)",
    flags=re.IGNORECASE,
)
CONTACT_TEXT_PATTERN = re.compile(
    r"(telephone:\s*\+?\d|www\.[a-z0-9.-]+|for more information, contact)",
    flags=re.IGNORECASE,
)


class DocumentProcessingPipeline:
    def __init__(self, output_dir: Path | None = None):
        self.output_dir = Path(output_dir or PROCESSED_DATA_DIR)
        self._chunk_counters = defaultdict(int)
        self._image_hash_counts = defaultdict(int)
        if pytesseract is not None and TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        self._ocr_available = Image is not None and pytesseract is not None

    def process_directory(self, raw_dir: Path | str):
        raw_path = Path(raw_dir)
        if not raw_path.exists():
            raise RuntimeError(f"Raw document directory not found: {raw_path}")

        processed_documents = []
        for pdf_path in sorted(raw_path.glob("*.pdf")):
            processed_documents.append(self.process_pdf(pdf_path))

        if not processed_documents:
            raise RuntimeError(f"No PDF files were found in: {raw_path}")

        return processed_documents

    def process_pdf(self, pdf_path: Path | str):
        pdf_path = Path(pdf_path)
        app_name = self._derive_app_name(pdf_path)
        app_output_dir = self.output_dir / self._slugify(app_name)
        images_output_dir = app_output_dir / "images"
        app_output_dir.mkdir(parents=True, exist_ok=True)
        images_output_dir.mkdir(parents=True, exist_ok=True)
        self._chunk_counters.clear()
        self._image_hash_counts.clear()

        try:
            document = fitz.open(pdf_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to open PDF document: {pdf_path}") from exc

        sections = []
        all_images = []
        chunk_index = 0

        try:
            for page_number in range(len(document)):
                page = document.load_page(page_number)
                blocks = self._extract_text_blocks(page)
                page_sections = self._detect_sections(blocks, page_number + 1)
                tables = self._extract_tables(page, page_number + 1)
                images = self._extract_images(
                    document,
                    page,
                    page_number + 1,
                    images_output_dir,
                )

                self._attach_tables_to_sections(page_sections, tables)
                self._attach_images_to_sections(page_sections, images)

                for section in page_sections:
                    section["app_name"] = app_name
                    section["source"] = str(pdf_path)
                    section["document_name"] = pdf_path.name
                    section["section_id"] = (
                        f"{self._slugify(app_name)}-p{section['page_number']}-{chunk_index}"
                    )
                    section["domain"] = self._classify_section(
                        section["section_title"],
                        section["text"],
                    )
                    section["metadata"] = self._build_metadata(section)
                    sections.append(section)
                    chunk_index += 1

                all_images.extend(images)
        finally:
            document.close()

        sections = self._rebalance_sections(sections)
        domain_chunks = self._build_domain_chunk_records(sections)
        files = self._write_domain_jsonl_files(app_output_dir, domain_chunks)

        return {
            "app_name": app_name,
            "source": str(pdf_path),
            "output_dir": str(app_output_dir),
            "files": files,
            "chunks_by_domain": domain_chunks,
            "image_count": len(all_images),
            "ocr_enabled": self._ocr_available,
            "section_count": len(sections),
        }

    def _extract_text_blocks(self, page):
        page_dict = page.get_text("dict")
        blocks = []

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            lines = []
            max_font_size = 0.0
            bold = False

            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = "".join(span.get("text", "") for span in spans).strip()
                if not line_text:
                    continue

                lines.append(line_text)
                for span in spans:
                    max_font_size = max(max_font_size, float(span.get("size", 0.0)))
                    if "bold" in str(span.get("font", "")).lower():
                        bold = True

            text = "\n".join(lines).strip()
            if not text:
                continue

            blocks.append(
                {
                    "text": text,
                    "bbox": block.get("bbox") or (0, 0, 0, 0),
                    "font_size": max_font_size,
                    "is_bold": bold,
                }
            )

        return blocks

    def _detect_sections(self, blocks, page_number):
        sections = []
        current = None

        for block in blocks:
            text = block["text"]
            if self._is_section_heading(text, block):
                if current:
                    sections.append(current)

                current = {
                    "page_number": page_number,
                    "section_title": self._clean_heading(text),
                    "text_blocks": [],
                    "images": [],
                    "tables": [],
                    "bbox": block["bbox"],
                }
                continue

            if current is None:
                current = {
                    "page_number": page_number,
                    "section_title": self._fallback_title(text),
                    "text_blocks": [],
                    "images": [],
                    "tables": [],
                    "bbox": block["bbox"],
                }

            current["text_blocks"].append(text)
            current["bbox"] = self._merge_bbox(current["bbox"], block["bbox"])

        if current:
            sections.append(current)

        for section in sections:
            section["text"] = self._normalize_text("\n\n".join(section["text_blocks"]))

        return [
            section
            for section in sections
            if section.get("text") or section.get("section_title")
        ]

    def _extract_tables(self, page, page_number):
        tables = []
        finder = getattr(page, "find_tables", None)
        if not callable(finder):
            return tables

        try:
            table_finder = finder()
        except Exception:
            return tables

        for index, table in enumerate(getattr(table_finder, "tables", [])):
            rows = table.extract() or []
            normalized_rows = [
                [self._normalize_text(str(cell or "")) for cell in row]
                for row in rows
                if any(str(cell or "").strip() for cell in row)
            ]
            if not normalized_rows:
                continue

            tables.append(
                {
                    "table_id": f"page-{page_number}-table-{index}",
                    "page_number": page_number,
                    "bbox": tuple(table.bbox),
                    "rows": normalized_rows,
                    "text": self._table_to_text(normalized_rows),
                }
            )

        return tables

    def _extract_images(self, document, page, page_number, images_output_dir):
        images = []
        for index, image in enumerate(page.get_images(full=True)):
            xref = image[0]
            try:
                base_image = document.extract_image(xref)
            except Exception:
                continue

            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []

            image_bytes = base_image.get("image")
            if not image_bytes or len(image_bytes) < MIN_IMAGE_BYTES:
                continue

            width = int(base_image.get("width") or 0)
            height = int(base_image.get("height") or 0)
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                continue

            image_hash = hashlib.sha1(image_bytes).hexdigest()
            self._image_hash_counts[image_hash] += 1
            if self._image_hash_counts[image_hash] > MAX_DUPLICATE_IMAGE_REUSE:
                continue

            bbox = tuple(rects[0]) if rects else (0, 0, 0, 0)
            extension = base_image.get("ext", "png")
            image_filename = f"page_{page_number:03d}_img_{index:03d}.{extension}"
            image_path = images_output_dir / image_filename
            image_path.write_bytes(image_bytes)
            extracted_text = self._extract_image_text(
                page=page,
                bbox=bbox,
                image_bytes=image_bytes,
            )

            images.append(
                {
                    "image_id": f"page-{page_number}-image-{index}",
                    "page_number": page_number,
                    "bbox": bbox,
                    "extension": extension,
                    "mime_type": f"image/{extension}",
                    "image_path": str(image_path),
                    "width": width,
                    "height": height,
                    "extracted_text": extracted_text,
                }
            )

        return images

    def _attach_tables_to_sections(self, sections, tables):
        for table in tables:
            section = self._match_section_by_bbox(sections, table["bbox"])
            if section is None:
                continue

            section["tables"].append(table)
            section["text_blocks"].append(table["text"])
            section["text"] = self._normalize_text("\n\n".join(section["text_blocks"]))

    def _attach_images_to_sections(self, sections, images):
        for image in images:
            section = self._match_section_by_bbox(sections, image["bbox"])
            if section is None:
                continue

            image["description"] = self._generate_image_caption(image, section)
            section["images"].append(
                {
                    "image_id": image["image_id"],
                    "page_number": image["page_number"],
                    "mime_type": image["mime_type"],
                    "description": image["description"],
                    "extracted_text": image.get("extracted_text", ""),
                    "image_path": image["image_path"],
                    "width": image["width"],
                    "height": image["height"],
                }
            )

    def _match_section_by_bbox(self, sections, bbox):
        if not sections:
            return None

        if bbox == (0, 0, 0, 0):
            return sections[-1]

        target_mid_y = (bbox[1] + bbox[3]) / 2
        best_section = None
        best_distance = None

        for section in sections:
            section_bbox = section.get("bbox") or (0, 0, 0, 0)
            section_mid_y = (section_bbox[1] + section_bbox[3]) / 2
            distance = abs(section_mid_y - target_mid_y)

            if best_distance is None or distance < best_distance:
                best_section = section
                best_distance = distance

        return best_section

    def _build_metadata(self, section):
        return {
            "app_name": section["app_name"],
            "domain": section["domain"],
            "section": section["section_title"],
            "source": section["source"],
            "document_name": section["document_name"],
            "page_number": section["page_number"],
            "image_count": len(section["images"]),
            "table_count": len(section["tables"]),
        }

    def _build_domain_chunk_records(self, sections):
        grouped = {domain: [] for domain in SUPPORTED_DOMAINS}

        for section in sections:
            grouped[section["domain"]].extend(self._build_records_for_section(section))

        return grouped

    def _rebalance_sections(self, sections):
        normalized = []
        for section in sections:
            if not self._should_keep_section(section):
                continue

            prepared = dict(section)
            prepared["text"] = self._normalize_text(prepared.get("text", ""))
            normalized.append(prepared)

        merged = []
        for section in normalized:
            if not merged:
                merged.append(section)
                continue

            previous = merged[-1]
            if self._should_merge_sections(previous, section):
                merged[-1] = self._merge_sections(previous, section)
            else:
                merged.append(section)

        split_sections = []
        for section in merged:
            split_sections.extend(self._split_section(section))

        finalized = []
        for index, section in enumerate(split_sections):
            finalized_section = dict(section)
            finalized_section["section_id"] = finalized_section.get("section_id") or (
                f"{self._slugify(finalized_section['app_name'])}-{index}"
            )
            finalized_section["metadata"] = self._build_metadata(finalized_section)
            finalized.append(finalized_section)

        return finalized

    def _write_domain_jsonl_files(self, app_output_dir, chunks_by_domain):
        files = {}
        for domain, chunks in chunks_by_domain.items():
            file_path = app_output_dir / f"{domain}_chunks.jsonl"
            with open(file_path, "w", encoding="utf-8") as handle:
                for chunk in chunks:
                    handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            files[domain] = str(file_path)
        return files

    def _classify_section(self, title, text):
        content = f"{title}\n{text}".lower()
        scores = defaultdict(int)

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                pattern = rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])"
                scores[domain] += len(re.findall(pattern, content))

        best_domain = max(SUPPORTED_DOMAINS, key=lambda domain: scores[domain])
        if scores[best_domain] == 0:
            return "patient"
        return best_domain

    def _generate_image_caption(self, image, section):
        parts = [
            f"{section['section_title']} illustration",
            f"page {image['page_number']}",
        ]

        width = image.get("width")
        height = image.get("height")
        if width and height:
            parts.append(f"{width}x{height}")

        snippet = self._short_snippet(section.get("text", ""))
        if snippet:
            parts.append(f"context: {snippet}")

        return ", ".join(parts)

    def _should_keep_section(self, section):
        title = self._normalize_space(section.get("section_title", ""))
        text = self._normalize_text(section.get("text", ""))
        images = section.get("images") or []
        tables = section.get("tables") or []
        page_number = int(section.get("page_number") or 0)

        if self._is_structural_noise_section(title, text, page_number):
            return False

        if not text:
            return (
                bool(images)
                and len(title) >= MIN_IMAGE_ONLY_TITLE_CHARS
                and not self._is_noise_title(title)
            )

        if self._is_noise_title(title):
            return False

        if text and self._is_noise_text(text) and not images and not tables:
            return False

        if len(text) >= MIN_SECTION_TEXT_CHARS:
            return True

        if self._looks_like_instruction_steps(text):
            return True

        if tables and (text or title):
            return True

        if images and len(title) >= MIN_IMAGE_ONLY_TITLE_CHARS:
            return True

        return False

    def _looks_like_instruction_steps(self, text):
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return False

        step_like_lines = sum(1 for line in lines if STEP_LINE_PATTERN.match(line))
        return step_like_lines >= 2

    def _is_structural_noise_section(self, title, text, page_number):
        title_lower = title.lower()
        text_normalized = self._normalize_space(text)
        text_lower = text_normalized.lower()

        if self._looks_like_table_of_contents(title_lower, text_normalized):
            return True

        if page_number <= 3 and (
            LEGAL_TEXT_PATTERN.search(text_lower)
            or CONTACT_TEXT_PATTERN.search(text_lower)
        ):
            return True

        if page_number <= 2 and not text and self._looks_like_cover_title(title_lower):
            return True

        return False

    def _looks_like_table_of_contents(self, title, text):
        if title in {"contents", "table of contents"}:
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 5:
            return False

        toc_like_lines = sum(1 for line in lines if TOC_LINE_PATTERN.search(line))
        return toc_like_lines >= max(4, len(lines) // 3)

    def _looks_like_cover_title(self, title):
        return (
            "user manual" in title
            or "provider portal" in title
            or "connected health" in title
        )

    def _should_merge_sections(self, left, right):
        if left.get("domain") != right.get("domain"):
            return False

        left_has_media = bool(left.get("images") or left.get("tables"))
        right_has_media = bool(right.get("images") or right.get("tables"))
        left_text = left.get("text", "")
        right_text = right.get("text", "")
        combined_length = len(left_text) + len(right_text)

        if left_has_media or right_has_media:
            return combined_length <= MAX_MULTIMODAL_TEXT_CHARS and self._is_related_section_pair(left, right)

        small_pair = (
            len(left_text) < MIN_SECTION_TEXT_CHARS
            or len(right_text) < MIN_SECTION_TEXT_CHARS
            or combined_length <= MERGE_TARGET_CHARS
        )
        return small_pair and self._is_related_section_pair(left, right)

    def _merge_sections(self, left, right):
        merged = dict(left)
        merged["section_title"] = self._choose_merged_title(left, right)
        merged["text_blocks"] = (left.get("text_blocks") or []) + (right.get("text_blocks") or [])
        merged["images"] = (left.get("images") or []) + (right.get("images") or [])
        merged["tables"] = (left.get("tables") or []) + (right.get("tables") or [])
        merged["text"] = self._normalize_text(
            "\n\n".join(part for part in [left.get("text", ""), right.get("text", "")] if part)
        )
        merged["bbox"] = self._merge_bbox(
            left.get("bbox") or (0, 0, 0, 0),
            right.get("bbox") or (0, 0, 0, 0),
        )
        merged["page_number"] = min(left.get("page_number", 1), right.get("page_number", 1))
        merged["section_id"] = left.get("section_id")
        return merged

    def _split_section(self, section):
        text = section.get("text", "")
        has_media = bool(section.get("images") or section.get("tables"))
        limit = MAX_MULTIMODAL_TEXT_CHARS if has_media else MAX_SECTION_TEXT_CHARS

        if len(text) <= limit:
            section["part"] = 1
            return [section]

        parts = self._split_text_into_parts(text, limit=limit)
        if len(parts) <= 1:
            section["part"] = 1
            return [section]

        split_sections = []
        total_parts = len(parts)
        for index, part_text in enumerate(parts, start=1):
            split_section = dict(section)
            split_section["text"] = part_text
            split_section["part"] = index
            split_section["section_id"] = f"{section['section_id']}-part-{index}"
            split_section["section_title"] = (
                section["section_title"]
                if total_parts == 1
                else f"{section['section_title']} (Part {index})"
            )
            if index > 1:
                split_section["images"] = []
                split_section["tables"] = []
            split_sections.append(split_section)

        return split_sections

    def _build_records_for_section(self, section):
        records = [
            self._build_chunk_record(
                section=section,
                chunk_type="text",
                text=section.get("text", ""),
                image_path=None,
            )
        ]

        for image in section.get("images") or []:
            records.append(
                self._build_chunk_record(
                    section=section,
                    chunk_type="image",
                    text=self._build_image_chunk_text(image, section),
                    image_path=image.get("image_path"),
                )
            )

        for table in section.get("tables") or []:
            records.append(
                self._build_chunk_record(
                    section=section,
                    chunk_type="table",
                    text=table.get("text", ""),
                    image_path=None,
                )
            )

        return [record for record in records if self._is_valid_chunk_record(record)]

    def _build_chunk_record(self, section, chunk_type, text, image_path):
        app_slug = self._slugify(section["app_name"])
        self._chunk_counters[(app_slug, chunk_type)] += 1
        sequence = self._chunk_counters[(app_slug, chunk_type)]

        return {
            "chunk_id": self._build_chunk_id(app_slug, chunk_type, sequence),
            "app": section["app_name"],
            "domain": section["domain"],
            "type": chunk_type,
            "text": self._normalize_text(text),
            "image_path": image_path,
            "section": section["section_title"],
            "page": section["page_number"],
            "keywords": self._extract_keywords(section, chunk_type, text),
        }

    def _build_chunk_id(self, app_slug, chunk_type, sequence):
        suffix_map = {"text": "txt", "image": "img", "table": "tbl"}
        suffix = suffix_map.get(chunk_type, chunk_type)
        return f"{app_slug}_{suffix}_{sequence:03d}"

    def _is_valid_chunk_record(self, record):
        text = self._normalize_text(record.get("text", ""))
        chunk_type = record.get("type")
        if chunk_type == "image":
            return bool(record.get("image_path")) and bool(text)
        return bool(text)

    def _build_image_chunk_text(self, image, section):
        extracted_text = self._normalize_text(image.get("extracted_text", ""))
        description = self._normalize_text(
            image.get("description") or section.get("section_title", "")
        )

        if extracted_text and description:
            return f"{extracted_text}\n\nImage context: {description}"
        if extracted_text:
            return extracted_text
        return description

    def _extract_keywords(self, section, chunk_type, text):
        candidates = [
            section.get("domain", ""),
            section.get("section_title", ""),
            chunk_type,
        ]
        candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9/-]{2,}", text or ""))

        keywords = []
        seen = set()
        stop_words = {
            "the", "and", "for", "with", "from", "this", "that", "page",
            "part", "section", "figure", "table", "app", "user", "guide",
        }

        for candidate in candidates:
            normalized = self._normalize_keyword(candidate)
            if not normalized or normalized in stop_words or normalized in seen:
                continue
            seen.add(normalized)
            keywords.append(normalized)
            if len(keywords) >= 8:
                break

        return keywords

    def _normalize_keyword(self, value):
        normalized = self._normalize_space(str(value)).lower()
        normalized = re.sub(r"[^a-z0-9/+ -]", "", normalized)
        normalized = normalized.strip(" -")
        if len(normalized) < 3:
            return ""
        return normalized

    def _extract_image_text(self, page, bbox, image_bytes):
        text_fragments = []

        clipped_text = self._extract_text_from_bbox(page, bbox)
        if clipped_text:
            text_fragments.append(clipped_text)

        ocr_text = self._extract_text_with_ocr(image_bytes)
        if ocr_text:
            text_fragments.append(ocr_text)

        return self._merge_text_fragments(text_fragments)

    def _extract_text_from_bbox(self, page, bbox):
        if not bbox or bbox == (0, 0, 0, 0):
            return ""

        try:
            clipped_text = page.get_text("text", clip=fitz.Rect(bbox))
        except Exception:
            return ""

        return self._normalize_text(clipped_text)

    def _extract_text_with_ocr(self, image_bytes):
        if not self._ocr_available:
            return ""

        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                prepared = image.convert("L")
                extracted_text = pytesseract.image_to_string(prepared)
        except Exception:
            return ""

        return self._normalize_text(extracted_text)

    def _merge_text_fragments(self, fragments):
        merged = []
        seen = set()

        for fragment in fragments:
            normalized = self._normalize_text(fragment)
            if not normalized:
                continue

            key = normalized.lower()
            if key in seen:
                continue

            seen.add(key)
            merged.append(normalized)

        return "\n\n".join(merged)

    def _split_text_into_parts(self, text, limit):
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        if len(paragraphs) <= 1:
            return self._split_long_paragraph(text, limit)

        parts = []
        current = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)
            if paragraph_length > limit:
                if current:
                    parts.append("\n\n".join(current))
                    current = []
                    current_length = 0
                parts.extend(self._split_long_paragraph(paragraph, limit))
                continue

            projected = current_length + paragraph_length + (2 if current else 0)
            if current and projected > limit:
                parts.append("\n\n".join(current))
                current = [paragraph]
                current_length = paragraph_length
            else:
                current.append(paragraph)
                current_length = projected

        if current:
            parts.append("\n\n".join(current))

        return [self._normalize_text(part) for part in parts if self._normalize_text(part)]

    def _split_long_paragraph(self, text, limit):
        sentences = re.split(r"(?<=[.!?])\s+", self._normalize_space(text))
        parts = []
        current = []
        current_length = 0

        for sentence in sentences:
            if not sentence:
                continue

            sentence_length = len(sentence)
            projected = current_length + sentence_length + (1 if current else 0)
            if current and projected > limit:
                parts.append(" ".join(current))
                current = [sentence]
                current_length = sentence_length
            else:
                current.append(sentence)
                current_length = projected

        if current:
            parts.append(" ".join(current))

        return [part.strip() for part in parts if part.strip()]

    def _is_related_section_pair(self, left, right):
        left_page = left.get("page_number", 1)
        right_page = right.get("page_number", 1)
        if abs(left_page - right_page) > 1:
            return False

        left_title = self._normalize_space(left.get("section_title", "")).lower()
        right_title = self._normalize_space(right.get("section_title", "")).lower()

        if left_title == right_title:
            return True

        if self._looks_like_caption(left_title) or self._looks_like_caption(right_title):
            return True

        return self._title_overlap(left_title, right_title) >= 1

    def _choose_merged_title(self, left, right):
        left_title = self._normalize_space(left.get("section_title", ""))
        right_title = self._normalize_space(right.get("section_title", ""))

        if self._looks_like_caption(left_title) and not self._looks_like_caption(right_title):
            return right_title
        if self._looks_like_caption(right_title) and not self._looks_like_caption(left_title):
            return left_title
        if len(left_title) >= len(right_title):
            return left_title or right_title
        return right_title or left_title

    def _is_noise_title(self, title):
        normalized = self._normalize_space(title).lower()
        if not normalized:
            return True
        if len(normalized) <= 2 and normalized not in {"rx"}:
            return True
        return any(re.match(pattern, normalized) for pattern in NOISE_TITLE_PATTERNS)

    def _is_noise_text(self, text):
        normalized = self._normalize_space(text).lower()
        if not normalized:
            return True
        if any(re.match(pattern, normalized) for pattern in NOISE_TEXT_PATTERNS):
            return True
        if len(normalized) < MIN_SECTION_TEXT_CHARS and self._looks_like_caption(normalized):
            return True
        return False

    def _looks_like_caption(self, value):
        normalized = self._normalize_space(value).lower()
        return (
            normalized.startswith("figure ")
            or normalized.startswith("table ")
            or normalized.startswith("chapter ")
            or normalized.startswith("note:")
            or normalized.startswith("warning:")
            or normalized.startswith("caution:")
        )

    def _title_overlap(self, left_title, right_title):
        left_tokens = {token for token in re.findall(r"[a-z0-9]+", left_title) if len(token) > 2}
        right_tokens = {token for token in re.findall(r"[a-z0-9]+", right_title) if len(token) > 2}
        return len(left_tokens & right_tokens)

    def _is_section_heading(self, text, block):
        normalized = self._normalize_space(text)
        lowered = normalized.lower()
        if not normalized:
            return False

        short_heading = len(normalized) <= 80 and "\n" not in normalized
        uppercase_ratio = self._uppercase_ratio(normalized)
        has_domain_keyword = any(
            re.search(rf"\b{re.escape(keyword)}\b", lowered)
            for keywords in DOMAIN_KEYWORDS.values()
            for keyword in keywords
        )

        if has_domain_keyword and short_heading:
            return (
                block.get("font_size", 0) >= 11
                or block.get("is_bold")
                or uppercase_ratio > 0.45
                or normalized.endswith(":")
            )

        return short_heading and (
            block.get("font_size", 0) >= 13
            or block.get("is_bold")
            or uppercase_ratio > 0.7
            or normalized.endswith(":")
        )

    def _fallback_title(self, text):
        first_line = self._normalize_space(text.splitlines()[0])
        if len(first_line) > 48:
            first_line = first_line[:45].rstrip() + "..."
        return first_line or "General"

    def _clean_heading(self, text):
        heading = self._normalize_space(text.replace("\n", " "))
        return heading.rstrip(":") or "General"

    def _derive_app_name(self, pdf_path):
        stem = pdf_path.stem
        stem = re.sub(r"[_-]userguide$", "", stem, flags=re.IGNORECASE)
        stem = re.sub(r"[_-]guide$", "", stem, flags=re.IGNORECASE)
        return re.sub(r"[_-]+", " ", stem).strip() or stem

    def _table_to_text(self, rows):
        formatted_rows = [" | ".join(cell for cell in row if cell) for row in rows]
        formatted_rows = [row for row in formatted_rows if row]
        return self._normalize_text("\n".join(formatted_rows))

    def _normalize_text(self, text):
        normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = normalized.replace("\u00e2\u20ac\u00a2", "\u2022")
        normalized = normalized.replace("â€¢", "\u2022")
        normalized = re.sub(r"[ \t]+\n", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _normalize_space(self, value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _uppercase_ratio(self, value):
        letters = [char for char in value if char.isalpha()]
        if not letters:
            return 0.0
        uppercase = sum(1 for char in letters if char.isupper())
        return uppercase / len(letters)

    def _short_snippet(self, text, limit=140):
        snippet = self._normalize_space(text)
        if len(snippet) <= limit:
            return snippet
        return snippet[: limit - 3].rstrip() + "..."

    def _slugify(self, value):
        slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
        return slug or "app"

    def _merge_bbox(self, left, right):
        return (
            min(left[0], right[0]),
            min(left[1], right[1]),
            max(left[2], right[2]),
            max(left[3], right[3]),
        )
