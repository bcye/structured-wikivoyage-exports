import fs from "fs";
import https from "https";
import path from "path";
import sax from "sax";
import bz2 from "unbzip2-stream";
import { createGunzip } from "zlib";

// Local storage configuration
const OUTPUT_FOLDER = "myfolder";

// --- Step 1: Fetch mappings from SQL dump ---
async function fetchMappings(): Promise<Record<string, string>> {
  return new Promise((resolve, reject) => {
    const sqlUrl =
      "https://dumps.wikimedia.org/enwikivoyage/latest/enwikivoyage-latest-page_props.sql.gz";
    https
      .get(sqlUrl, (res) => {
        if (res.statusCode !== 200) {
          return reject(
            new Error(`Failed to get SQL dump, status code: ${res.statusCode}`),
          );
        }
        const gunzip = createGunzip();
        let buffer = "";
        const mappings: Record<string, string> = {};
        res.pipe(gunzip);
        gunzip.on("data", (chunk: Buffer) => {
          buffer += chunk.toString();
          const regex = /\((\d+),'([^']+)','([^']+)',(NULL|[\d\.]+)\)/g;
          let match: RegExpExecArray | null;
          while ((match = regex.exec(buffer)) !== null) {
            const [, pp_page, pp_propname, pp_value] = match;
            if (pp_propname === "wikibase_item") {
              mappings[pp_page] = pp_value;
            }
          }
          // Keep a tail to handle chunk splits
          if (buffer.length > 1000) {
            buffer = buffer.slice(-1000);
          }
        });
        gunzip.on("end", () => resolve(mappings));
        gunzip.on("error", reject);
      })
      .on("error", reject);
  });
}

// --- Helper to save file locally ---
let saveCount = 0;
function saveToLocalFile(filename: string, data: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // Create directory if it doesn't exist
    if (!fs.existsSync(OUTPUT_FOLDER)) {
      fs.mkdirSync(OUTPUT_FOLDER, { recursive: true });
    }
    
    const filePath = path.join(OUTPUT_FOLDER, filename);
    fs.writeFile(filePath, data, (err) => {
      if (err) {
        reject(err);
      } else {
        console.log(`File saved successfully (${++saveCount}): ${filePath}`);
        resolve();
      }
    });
  });
}

// Simple semaphore to limit concurrency
class Semaphore {
  private tasks: (() => void)[] = [];
  private count: number;
  constructor(count: number) {
    this.count = count;
  }
  async acquire(): Promise<() => void> {
    return new Promise((release) => {
      const task = () => {
        this.count--;
        release(() => {
          this.count++;
          if (this.tasks.length > 0) {
            const next = this.tasks.shift()!;
            next();
          }
        });
      };
      if (this.count > 0) {
        task();
      } else {
        this.tasks.push(task);
      }
    });
  }
}

// --- Step 3: Process the XML dump ---
async function processXML(mappings: Record<string, string>): Promise<void> {
  return new Promise((resolve, reject) => {
    const xmlUrl =
      "https://dumps.wikimedia.org/enwikivoyage/latest/enwikivoyage-latest-pages-articles.xml.bz2";
    https
      .get(xmlUrl, (res) => {
        if (res.statusCode !== 200) {
          return reject(
            new Error(`Failed to fetch XML dump: ${res.statusCode}`),
          );
        }
        // Pipe through bz2 decompressor
        const stream = res.pipe(bz2());
        // Use sax for streaming XML parsing
        const parser = sax.createStream(true, {});
        let currentPageId: string | null = null;
        let currentText: string | null = null;
        let inPage = false;
        let inRevision = false;
        let inText = false;
        let currentTag: string | null = null; // Track current tag
        parser.on("opentag", (node) => {
          currentTag = node.name; // Track current tag
          if (node.name === "page") {
            inPage = true;
            currentPageId = null;
            currentText = null;
          } else if (node.name === "revision") {
            inRevision = true;
          } else if (inRevision && node.name === "text") {
            inText = true;
          }
        });
        parser.on("closetag", (tagName) => {
          if (tagName === "page") {
            if (
              typeof currentPageId == "string" &&
              currentText !== null &&
              !!mappings[currentPageId]
            ) {
              const wikidataId = mappings[currentPageId];
              const filename = `${wikidataId}.wiki.txt`;
              
              // Make a copy as the value will continue changing
              const textToSave = currentText.toString();
              

                  saveToLocalFile(filename, textToSave).catch((err) =>
                  console.error(`Save error for page ${currentPageId}:`, err)
                );
            }
            // Reset state for the next page
            inPage = false;
            currentPageId = null;
            currentText = null;
          } else if (tagName === "revision") {
            inRevision = false;
          } else if (tagName === "text") {
            inText = false;
          }
          currentTag = null; // Reset current tag
        });
        parser.on("text", (text) => {
          const trimmedText = text.trim();
          if (!trimmedText) return;
          if (currentTag === "id" && inPage && !inRevision && !currentPageId) {
            currentPageId = trimmedText;
          } else if (inText) {
            currentText = (currentText || "") + trimmedText;
          }
        });
        parser.on("error", reject);
        parser.on("end", resolve);
        stream.pipe(parser);
      })
      .on("error", reject);
  });
}

// --- Main integration ---
async function main() {
  try {
    console.log("Fetching mappings from SQL dump...");
    const mappings = await fetchMappings();
    console.log(`Fetched ${Object.keys(mappings).length} mappings.`);
    console.log("Processing XML dump...");
    await processXML(mappings);
    console.log("Processing complete.");
  } catch (err) {
    console.error("Error:", err);
  }
}

main().then(() => process.exit());