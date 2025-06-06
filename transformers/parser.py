"""Where the magic happens: parsing wikitext into a structured JSON tree."""
import mwparserfromhell as mwp
import mwparserfromhell.nodes as nodes
import json
from typing import Dict


DOCUMENT_TEMPLATES = [
    "pagebanner", "mapframe", "routebox", "geo", "isPartOf",
    "usablecity", "guidecity", "outlinecity"
]
LISTING_TEMPLATES = [
    "see", "do", "buy", "eat", "drink", "sleep", "listing"
]

class WikivoyageParser:
    """
    A parser for Wikivoyage wikitext to JSON tree structure.
    This class uses mwparserfromhell to parse the wikitext and convert it into a structured JSON format.
    """
    def __init__(self):
        self.root = {
            "type": "root",
            "properties": {},
            "children": []
        }
        self.current_section = self.root

    def parse(self, wikitext: str) -> Dict:
        """Parse wikitext and return structured JSON tree"""
        self.root = {
            "type": "root",
            "properties": {},
            "children": []
        }
        self.current_section = self.root
        
        # Parse the wikitext
        parsed = mwp.parse(wikitext)
        
        # Process the parsed content
        self._process_nodes(parsed)
        
        return self.root

    def _process_nodes(self, wikicode):
        """Process all nodes in the wikicode"""
        current_text = ""
        
        for node in wikicode.nodes:
            # Handle different node types
            if isinstance(node, nodes.heading.Heading):
                # First flush any pending text
                if current_text:
                    self._add_text_node(current_text)
                    current_text = ""
                
                # Create new section
                self._handle_heading(node)
                
            elif isinstance(node, nodes.template.Template):
                # First flush any pending text
                if current_text:
                    self._add_text_node(current_text)
                    current_text = ""
                
                # Handle template
                self._handle_template(node)
                
            elif isinstance(node, nodes.text.Text):
                # Accumulate text
                current_text += str(node.value)
                
            elif isinstance(node, nodes.tag.Tag):
                # Handle tag (potential styling)
                tag_text = self._convert_tag_to_markdown(node)
                current_text += tag_text
                
            elif isinstance(node, nodes.wikilink.Wikilink):
                # Handle wikilink
                link_text = self._convert_wikilink_to_markdown(node)
                current_text += link_text
                
            elif isinstance(node, nodes.external_link.ExternalLink):
                # Handle external link
                link_text = self._convert_external_link_to_markdown(node)
                current_text += link_text
                
            elif isinstance(node, nodes.comment.Comment):
                # Skip comments
                pass
                
            else:
                # Process other nodes as text
                current_text += str(node)
        
        # Add any remaining text
        if current_text:
            self._add_text_node(current_text)

    def _add_text_node(self, text: str):
        """Add a text node to the current section"""
        # Avoid adding empty text nodes
        if not text.strip():
            return
            
        text_node = {
            "type": "text",
            "properties": {
                "markdown": text.strip()
            },
            "children": []
        }
        
        self.current_section["children"].append(text_node)

    def _handle_heading(self, heading_node):
        """Handle a heading node by creating a new section"""
        level = heading_node.level
        title = str(heading_node.title).strip()
        
        # Create new section node
        section = {
            "type": "section",
            "properties": {
                "title": title,
                "level": level
            },
            "children": []
        }
        
        # Find the appropriate parent section based on level
        parent = self.root
        
        # If the level is 1, the parent is the root
        if level > 1:
            # Start from root and traverse the tree
            current = self.root
            current_level = 0
            
            for child in reversed(self._get_all_sections()):
                child_level = child["properties"]["level"]
                if child_level < level:
                    parent = child
                    break
        
        # Add the section to its parent
        parent["children"].append(section)
        
        # Update current section
        self.current_section = section

    def _get_all_sections(self):
        """Get all sections in the document in the order they appear"""
        sections = []
        
        def collect_sections(node):
            if node["type"] == "section":
                sections.append(node)
            for child in node["children"]:
                if child["type"] == "section":
                    collect_sections(child)
        
        collect_sections(self.root)
        return sections

    def _handle_template(self, template_node):
        """Handle a template node"""
        template_name = str(template_node.name).strip().lower()
        
        # Check if it's a document-wide template
        if template_name in DOCUMENT_TEMPLATES:
            self._handle_document_template(template_node)
            return
            
        # Check if it's a listing template
        if template_name in LISTING_TEMPLATES:
            self._handle_listing_template(template_node)
            return
            
        # Handle other templates as regular nodes
        self._handle_other_template(template_node)

    def _handle_document_template(self, template_node):
        """Handle document-wide templates by adding to root properties"""
        template_name = str(template_node.name).strip().lower()
        
        # Extract parameters
        params = {}
        for param in template_node.params:
            name = str(param.name).strip()
            value = str(param.value).strip()
            params[name] = value
            
        # Add to root properties
        if template_name not in self.root["properties"]:
            self.root["properties"][template_name] = {}
            
        self.root["properties"][template_name] = params

    def _handle_listing_template(self, template_node):
        """Handle listing templates (see, do, buy, eat, drink, sleep)"""
        template_name = str(template_node.name).strip().lower()
        
        # Extract parameters
        properties = {}
        for param in template_node.params:
            name = str(param.name).strip()
            value = str(param.value).strip()
            
            # Convert content to markdown if it's in the 'content' parameter
            if name == "content":
                value = self._convert_wikicode_to_markdown(param.value)
                
            properties[name] = value
            
        # Create listing node
        listing_node = {
            "type": template_name,
            "properties": properties,
            "children": []
        }
        
        # Add to current section
        self.current_section["children"].append(listing_node)

    def _handle_other_template(self, template_node):
        """Handle other templates as general template nodes"""
        template_name = str(template_node.name).strip().lower()
        
        # Extract parameters
        properties = {
            "name": template_name,
            "params": {}
        }
        
        for param in template_node.params:
            name = str(param.name).strip()
            value = str(param.value).strip()
            properties["params"][name] = value
            
        # Create template node
        template_node = {
            "type": "template",
            "properties": properties,
            "children": []
        }
        
        # Add to current section
        self.current_section["children"].append(template_node)

    def _convert_wikicode_to_markdown(self, wikicode) -> str:
        """Convert wikicode to markdown"""
        markdown = ""
        
        for node in wikicode.nodes:
            if isinstance(node, nodes.text.Text):
                markdown += str(node.value)
                
            elif isinstance(node, nodes.tag.Tag):
                markdown += self._convert_tag_to_markdown(node)
                
            elif isinstance(node, nodes.wikilink.Wikilink):
                markdown += self._convert_wikilink_to_markdown(node)
                
            elif isinstance(node, nodes.external_link.ExternalLink):
                markdown += self._convert_external_link_to_markdown(node)
                
            else:
                # For other nodes, just use their string representation
                markdown += str(node)
                
        return markdown.strip()

    def _convert_tag_to_markdown(self, tag_node) -> str:
        """Convert HTML tag to markdown"""
        tag = str(tag_node.tag).lower()
        content = str(tag_node.contents)
        
        # Convert the content recursively to handle nested tags
        if tag_node.contents:
            content = self._convert_wikicode_to_markdown(tag_node.contents)
            
        # Handle different tags
        if tag == 'b' or tag == 'strong':
            return f"**{content}**"
        elif tag == 'i' or tag == 'em':
            return f"*{content}*"
        elif tag == 'u':
            return f"_{content}_"
        elif tag == 'strike' or tag == 's' or tag == 'del':
            return f"~~{content}~~"
        elif tag == 'code':
            return f"`{content}`"
        elif tag == 'pre':
            return f"```\n{content}\n```"
        elif tag == 'br':
            return "\n"
        elif tag == 'hr':
            return "\n---\n"
        elif tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            return f"\n{'#' * level} {content}\n"
        elif tag == 'a':
            href = ""
            for attr in tag_node.attributes:
                if str(attr.name).lower() == 'href':
                    href = str(attr.value)
                    break
            return f"[{content}]({href})"
        elif tag == 'img':
            src = alt = ""
            for attr in tag_node.attributes:
                if str(attr.name).lower() == 'src':
                    src = str(attr.value)
                elif str(attr.name).lower() == 'alt':
                    alt = str(attr.value)
            return f"![{alt}]({src})"
        else:
            # For unknown tags, just return the content
            return content

    def _convert_wikilink_to_markdown(self, wikilink_node) -> str:
        """Convert wikilink to markdown"""
        title = str(wikilink_node.title)
        
        if wikilink_node.text:
            text = str(wikilink_node.text)
            return f"[{text}]({title})"
        else:
            return f"[{title}]({title})"

    def _convert_external_link_to_markdown(self, link_node) -> str:
        """Convert external link to markdown"""
        url = str(link_node.url)
        
        if link_node.title:
            title = str(link_node.title)
            return f"[{title}]({url})"
        else:
            return url

    def export_json(self, root=None, indent=2) -> str:
        """Export the tree as JSON string"""
        if root is None:
            root = self.root
            
        return json.dumps(root, indent=indent)
