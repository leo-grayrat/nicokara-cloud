import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { ProcessedLyrics } from "@/types/job";
import {
  buildReadingCorrections,
  ReadingReviewEditor,
} from "./reading-review-editor";

const lyrics: ProcessedLyrics = {
  provider: "local",
  source_text: "泣き声と強い意志",
  warnings: [],
  lines: [
    {
      source: "泣き声と強い意志",
      surface: "泣き声と強い意志",
      reading: "なきこえとつよいいし",
      tokens: [
        { surface: "泣", reading: "な" },
        { surface: "き", reading: "き" },
        { surface: "声", reading: "こえ" },
        { surface: "と", reading: "と" },
        { surface: "強", reading: "つよ" },
        { surface: "い", reading: "い" },
        { surface: "意", reading: "い" },
        { surface: "志", reading: "し" },
      ],
      review_units: [
        { start_token: 0, end_token: 3, surface: "泣き声", reading: "なきこえ" },
        { start_token: 4, end_token: 6, surface: "強い", reading: "つよい" },
        { start_token: 6, end_token: 8, surface: "意志", reading: "いし" },
      ],
    },
  ],
};

describe("ReadingReviewEditor", () => {
  it("renders server review units instead of internal tokens", () => {
    const html = renderToStaticMarkup(
      <ReadingReviewEditor lyrics={lyrics} submitting={false} onConfirm={vi.fn()} />,
    );

    expect(html).toContain('aria-label="泣き声 假名读音"');
    expect(html).toContain('aria-label="強い 假名读音"');
    expect(html).toContain('aria-label="意志 假名读音"');
    expect(html).not.toContain('aria-label="き 假名读音"');
    expect(html.match(/<input/g)).toHaveLength(3);
  });

  it("omits kana-only lines when the server has no review units", () => {
    const html = renderToStaticMarkup(
      <ReadingReviewEditor
        lyrics={{
          provider: "local",
          source_text: "きっと、またね",
          warnings: [],
          lines: [{
            source: "きっと、またね",
            surface: "きっと、またね",
            reading: "きっと、またね",
            tokens: [
              { surface: "きっと", reading: "きっと" },
              { surface: "、", reading: "、" },
              { surface: "またね", reading: "またね" },
            ],
            review_units: [],
          }],
        }}
        submitting={false}
        onConfirm={vi.fn()}
      />,
    );

    expect(html).toContain("没有需要人工确认的注音");
    expect(html).not.toContain("<input");
  });

  it("keeps the foreign-reading warning on server review units", () => {
    const html = renderToStaticMarkup(
      <ReadingReviewEditor
        lyrics={{
          provider: "local",
          source_text: "80億分の1 LOVE",
          warnings: [],
          lines: [{
            source: "80億分の1 LOVE",
            surface: "80億分の1 LOVE",
            reading: "80億分の1 LOVE",
            tokens: [
              { surface: "80億分の1", reading: "80億分の1" },
              { surface: " ", reading: " " },
              { surface: "LOVE", reading: "LOVE" },
            ],
            review_units: [
              {
                start_token: 0,
                end_token: 1,
                surface: "80億分の1",
                reading: "80億分の1",
              },
              {
                start_token: 2,
                end_token: 3,
                surface: "LOVE",
                reading: "LOVE",
              },
            ],
          }],
        }}
        submitting={false}
        onConfirm={vi.fn()}
      />,
    );

    expect(html).toContain("检测到 2 处英文或数字");
    expect(html.match(/aria-invalid="true"/g)).toHaveLength(2);
  });
});

describe("buildReadingCorrections", () => {
  it("submits only the review unit whose reading changed", () => {
    expect(buildReadingCorrections(lyrics, { "0:0:3": "なきごえ" })).toEqual({
      corrections: [{
        line_index: 0,
        start_token: 0,
        end_token: 3,
        surface: "泣き声",
        current_reading: "なきこえ",
        corrected_reading: "なきごえ",
      }],
    });
  });

  it("omits unchanged and blank edits", () => {
    expect(buildReadingCorrections(lyrics, {
      "0:0:3": "なきこえ",
      "0:4:6": "   ",
    })).toEqual({ corrections: [] });
  });
});
