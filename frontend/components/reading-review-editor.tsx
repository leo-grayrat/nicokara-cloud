"use client";

import { Check, LoaderCircle, TriangleAlert } from "lucide-react";
import { useState } from "react";

import type {
  ProcessedLyrics,
  ProcessedPronunciationSegment,
  ProcessedReadingReviewUnit,
  ReadingReviewPayload,
} from "@/types/job";

const LATIN_OR_DIGIT = /[A-Za-z0-9]/;

function reviewSegmentKey(
  lineIndex: number,
  startToken: number,
  endToken: number,
  segmentIndex: number,
) {
  return `${lineIndex}:${startToken}:${endToken}:${segmentIndex}`;
}

function isForeignSurface(surface: string) {
  return LATIN_OR_DIGIT.test(surface);
}

function hasUnconvertedForeignReading(surface: string, reading: string) {
  return isForeignSurface(surface)
    && (reading.trim().length === 0 || LATIN_OR_DIGIT.test(reading));
}

function reviewSegments(
  unit: ProcessedReadingReviewUnit,
): ProcessedPronunciationSegment[] {
  if (isForeignSurface(unit.surface) || !unit.pronunciation_segments?.length) {
    return [{
      surface_start: 0,
      surface_end: unit.surface.length,
      reading: unit.reading,
      ruby: true,
    }];
  }
  return unit.pronunciation_segments;
}

function rebuiltReading(
  unit: ProcessedReadingReviewUnit,
  lineIndex: number,
  editedReadings: Record<string, string>,
) {
  return reviewSegments(unit).map((segment, segmentIndex) => {
    if (!segment.ruby) return segment.reading;
    const edited = editedReadings[reviewSegmentKey(
      lineIndex,
      unit.start_token,
      unit.end_token,
      segmentIndex,
    )]?.trim();
    return edited || segment.reading;
  }).join("");
}

export function buildReadingCorrections(
  lyrics: ProcessedLyrics,
  editedReadings: Record<string, string>,
): ReadingReviewPayload {
  const corrections = lyrics.lines.flatMap((line, lineIndex) =>
    line.review_units.flatMap((unit) => {
      const corrected = rebuiltReading(unit, lineIndex, editedReadings);
      if (corrected === unit.reading) return [];
      return [{
        line_index: lineIndex,
        start_token: unit.start_token,
        end_token: unit.end_token,
        surface: unit.surface,
        current_reading: unit.reading,
        corrected_reading: corrected,
      }];
    }),
  );
  return { corrections };
}

export function ReadingReviewEditor({
  lyrics,
  submitting,
  onConfirm,
}: {
  lyrics: ProcessedLyrics;
  submitting: boolean;
  onConfirm: (review: ReadingReviewPayload) => void;
}) {
  const [editedReadings, setEditedReadings] = useState<Record<string, string>>(
    {},
  );
  const valid = lyrics.lines.length > 0;
  const reviewLines = lyrics.lines.map((line, lineIndex) => ({
    line,
    lineIndex,
    units: line.review_units,
  })).filter(({ units }) => units.length > 0);
  const foreignReadingCount = reviewLines.reduce(
    (count, { units }) => count + units.filter(
      (unit) => isForeignSurface(unit.surface),
    ).length,
    0,
  );

  return (
    <section className="mt-6 border-t pt-6" aria-labelledby="reading-review-heading">
      <h2 id="reading-review-heading" className="text-xl font-bold">
        确认假名注音
      </h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        请检查含汉字、英文或数字的读音；留空将沿用系统生成的读音。
      </p>
      {foreignReadingCount > 0 && (
        <div
          role="alert"
          className="mt-4 flex gap-3 rounded-md border border-amber-500/70 bg-amber-50 px-4 py-3 text-amber-950 shadow-sm dark:bg-amber-950/30 dark:text-amber-100"
        >
          <TriangleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <div className="min-w-0">
            <p className="font-bold">请确认将外来语注音为假名</p>
            <p className="mt-1 text-sm leading-6">
              检测到 {foreignReadingCount} 处英文或数字。系统已提供默认读音，
              请按实际唱法逐项确认高亮项目，例如 LOVE → らぶ。
            </p>
          </div>
        </div>
      )}
      {reviewLines.length === 0 ? (
        <p className="mt-4 rounded-md border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
          没有需要人工确认的注音。
        </p>
      ) : (
        <div className="mt-4 max-h-[34rem] divide-y overflow-y-auto overscroll-contain border-y [scrollbar-gutter:stable]">
          {reviewLines.map(({ line, lineIndex, units }) => (
            <section key={`${lineIndex}-${line.surface}`} className="py-4">
              <h3 className="break-all text-sm font-bold">
                {lineIndex + 1}. {line.surface}
              </h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {units.map((unit) => {
                  const key = `${lineIndex}:${unit.start_token}:${unit.end_token}`;
                  const segments = reviewSegments(unit);
                  const reading = rebuiltReading(unit, lineIndex, editedReadings);
                  const requiresKanaConfirmation = isForeignSurface(unit.surface);
                  const hasInvalidKana = hasUnconvertedForeignReading(
                    unit.surface,
                    reading,
                  );
                  return (
                    <div
                      key={key}
                      className={`min-w-0 text-xs font-medium ${
                        requiresKanaConfirmation
                          ? "rounded-md border border-amber-500/70 bg-amber-50 p-2 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100"
                          : "text-muted-foreground"
                      }`}
                    >
                      <span className="block break-all text-sm font-semibold text-foreground">
                        {unit.surface}
                      </span>
                      <div className="mt-1 flex flex-wrap items-end gap-1.5">
                        {segments.map((segment, segmentIndex) => {
                          const segmentSurface = unit.surface.slice(
                            segment.surface_start,
                            segment.surface_end,
                          );
                          if (!segment.ruby) {
                            return (
                              <span
                                key={`${key}:${segmentIndex}`}
                                aria-label={`${unit.surface} 中的固定假名`}
                                className="pb-2 text-sm font-normal text-foreground"
                              >
                                {segmentSurface}
                              </span>
                            );
                          }
                          const segmentKey = reviewSegmentKey(
                            lineIndex,
                            unit.start_token,
                            unit.end_token,
                            segmentIndex,
                          );
                          const singleWholeSegment = segments.length === 1
                            && segmentSurface === unit.surface;
                          return (
                            <label
                              key={segmentKey}
                              className="min-w-16 flex-1"
                            >
                              {!singleWholeSegment && (
                                <span className="block text-xs text-muted-foreground">
                                  {segmentSurface}
                                </span>
                              )}
                              <input
                                type="text"
                                value={editedReadings[segmentKey] ?? segment.reading}
                                aria-label={singleWholeSegment
                                  ? `${unit.surface} 假名读音`
                                  : `${unit.surface} 中 ${segmentSurface} 的假名读音`}
                                aria-invalid={hasInvalidKana || undefined}
                                disabled={submitting}
                                onChange={(event) => setEditedReadings((current) => ({
                                  ...current,
                                  [segmentKey]: event.target.value,
                                }))}
                                className={`focus-ring w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground disabled:opacity-60 ${
                                  requiresKanaConfirmation
                                    ? "border-amber-600 ring-2 ring-amber-400/50"
                                    : ""
                                }`}
                              />
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
      <button
        type="button"
        disabled={!valid || submitting}
        onClick={() => onConfirm(buildReadingCorrections(lyrics, editedReadings))}
        className="focus-ring mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? (
          <LoaderCircle className="size-4 animate-spin" />
        ) : (
          <Check className="size-4" />
        )}
        {submitting ? "正在保存" : "保存注音并开始对齐"}
      </button>
    </section>
  );
}
