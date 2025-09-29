from logging import getLogger
import xml.sax
import asyncio
from .parser import WikivoyageParser

logger = getLogger(__name__)


class WikiDumpHandler(xml.sax.ContentHandler):
    """
    SAX handler that, for each <page> whose <id> is in mappings,
    collects the <text> and schedules an async task to parse
    and write via the user‐supplied handler(s).
    """

    def __init__(self, mappings, handlers):
        super().__init__()
        self.mappings = mappings
        # Support a single handler or a list of handlers
        self.handlers = handlers
        self.tasks: list[asyncio.Task] = []

        self.currentTag: str | None = None
        self.inPage = False
        self.inRevision = False
        self.inText = False
        self.currentPageId: str | None = None
        self.currentTitle: str | None = None
        self.currentText: list[str] = []

    def startElement(self, name, attrs):
        self.currentTag = name
        if name == "page":
            logger.debug("start page")
            self.inPage = True
            self.currentPageId = None
            self.currentTitle = None
            self.currentText = []
        elif name == "revision":
            logger.debug("start revision")
            self.inRevision = True
        elif name == "text" and self.inRevision:
            logger.debug("start text")
            self.inText = True

    def endElement(self, name):
        if name == "page":
            logger.debug("end page")
            pid = self.currentPageId
            if pid and pid in self.mappings:
                wd_id = self.mappings[pid]
                text = "".join(self.currentText)
                title = self.currentTitle
                logger.debug(f"scheduled {wd_id} for handling")
                # schedule processing
                task = asyncio.create_task(self._process(text, wd_id, title))
                self.tasks.append(task)
            else:
                logger.debug(f"page {pid} without wikidata id, skipping...")
            # reset
            self.inPage = self.inRevision = self.inText = False
            self.currentPageId = None
            self.currentTitle = None
            self.currentText = []
        elif name == "revision":
            logger.debug("end revision")
            self.inRevision = False
        elif name == "text":
            logger.debug("end text")
            self.inText = False
        self.currentTag = None

    def characters(self, content):
        # Only filter whitespace for ID fields, preserve all content for text
        if (
            self.currentTag == "id"
            and self.inPage
            and not self.inRevision
            and not self.currentPageId
        ):
            content_stripped = content.strip()
            if content_stripped:  # Only process non-empty ID content
                self.currentPageId = content_stripped
        elif self.currentTag == "title" and self.inPage:
            if self.currentTitle is None:
                self.currentTitle = content
            else:
                self.currentTitle += content
        elif self.inText:
            # Always append text content, even if it's just whitespace or newlines
            self.currentText.append(content)

    async def _process(self, text: str, uid: str, title: str):
        parser = WikivoyageParser()
        entry = parser.parse(text)
        entry["properties"]["title"] = title

        # Write to all handlers concurrently
        await asyncio.gather(
            *[handler.write_entry(entry, uid) for handler in self.handlers]
        )
