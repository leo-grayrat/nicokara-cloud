"use client";

import { Check, LoaderCircle, TriangleAlert } from "lucide-react";

import type { ProcessedLyrics } from "@/types/job";

const LATIN_OR_DIGIT = /[A-Za-z0-9]/;
const KANJI_LATIN_OR_DIGIT = /[\p{Script=Han}A-Za-z0-9]/u;

function isForeignSurface(surface: string) {
  return LATIN_OR_DIGIT.test(surface);
}

function requiresReadingReview(surface: string) {
  return KANJI_LATIN_OR_DIGIT.test(surface);
}

function hasUnconvertedForeignReading(surface: string, reading: string) {
  return isForeignSurface(surface)
    && (reading.trim().length === 0 || LATIN_OR_DIGIT.test(reading));
}

export function ReadingReviewEditor({
  lyrics,
  submitting,
  onChange,
  onConfirm,
}: {
  lyrics: ProcessedLyrics;
  submitting: boolean;
  onChange: (lyrics: ProcessedLyrics) => void;
  onConfirm: () => void;
}) {
  const valid = lyrics.lines.length > 0 && lyrics.lines.every(
    (line) => line.tokens.length > 0,
  );
  const foreignReadingCount = lyrics.lines.reduce(
    (count, line) => count + line.tokens.filter(
      (token) => isForeignSurface(token.surface),
    ).length,
    0,
  );
  const reviewLines = lyrics.lines.map((line, lineIndex) => ({
    line,
    lineIndex,
    tokens: line.tokens.map((token, tokenIndex) => ({
      token,
      tokenIndex,
    })).filter(({ token }) => requiresReadingReview(token.surface)),
  })).filter(({ tokens }) => tokens.length > 0);

  function updateReading(
    lineIndex: number,
    tokenIndex: number,
    reading: string,
  ) {
    const lines = lyrics.lines.map((line, candidateLineIndex) => {
      if (candidateLineIndex !== lineIndex) return line;
      const tokens = line.tokens.map((token, candidateTokenIndex) =>
        candidateTokenIndex === tokenIndex
          ? { ...token, reading }
          : token,
      );
      return {
        ...line,
        reading: tokens.map((token) => token.reading).join(""),
        tokens,
      };
    });
    onChange({ ...lyrics, lines });
  }

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
          {reviewLines.map(({ line, lineIndex, tokens }) => (
            <section key={`${lineIndex}-${line.surface}`} className="py-4">
              <h3 className="break-all text-sm font-bold">
                {lineIndex + 1}. {line.surface}
              </h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {tokens.map(({ token, tokenIndex }) => {
                  const requiresKanaConfirmation = isForeignSurface(
                    token.surface,
                  );
                  const hasInvalidKana = hasUnconvertedForeignReading(
                    token.surface,
                    token.reading,
                  );
                  return (
                    <label
                      key={`${tokenIndex}-${token.surface}`}
                      className={`min-w-0 text-xs font-medium ${
                        requiresKanaConfirmation
                          ? "rounded-md border border-amber-500/70 bg-amber-50 p-2 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100"
                          : "text-muted-foreground"
                      }`}
                    >
                      <span className="block break-all text-sm font-semibold text-foreground">
                        {token.surface}
                      </span>
                      <span className="sr-only">假名读音</span>
                      <input
                        type="text"
                        value={token.reading}
                        aria-invalid={hasInvalidKana || undefined}
                        disabled={submitting}
                        onChange={(event) => updateReading(
                          lineIndex,
                          tokenIndex,
                          event.target.value,
                        )}
                        className={`focus-ring mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground disabled:opacity-60 ${
                          requiresKanaConfirmation
                            ? "border-amber-600 ring-2 ring-amber-400/50"
                            : ""
                        }`}
                      />
                    </label>
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
        onClick={onConfirm}
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
