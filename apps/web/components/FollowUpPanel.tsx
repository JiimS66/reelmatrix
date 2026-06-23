"use client";

import { FormEvent, useState } from "react";

interface FollowUpPanelProps {
  questions: string[];
  onSubmit: (answer: string) => void | Promise<void>;
  isLoading: boolean;
}

export function FollowUpPanel({
  questions,
  onSubmit,
  isLoading,
}: FollowUpPanelProps) {
  const [answer, setAnswer] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedAnswer = answer.trim();
    if (!normalizedAnswer) {
      setValidationError("Add your clarification before continuing.");
      return;
    }
    setValidationError(null);
    void onSubmit(normalizedAnswer);
  }

  return (
    <section className="panel border-amber-200 bg-amber-50/70">
      <p className="eyebrow text-amber-800">Clarification round</p>
      <h2 className="mt-2 text-2xl font-semibold text-ink">Sharpen the brief</h2>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        The campaign is not blocked. Answer the open questions and the same workflow
        will evaluate the updated context.
      </p>
      <ol className="mt-5 space-y-3">
        {questions.map((question, index) => (
          <li key={question} className="flex gap-3 text-sm leading-6 text-slate-700">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-200 text-xs font-bold text-amber-900">
              {index + 1}
            </span>
            <span>{question}</span>
          </li>
        ))}
      </ol>
      <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
        <label className="label" htmlFor="follow_up_answer">
          Your clarification
        </label>
        <textarea
          id="follow_up_answer"
          className="input min-h-32 resize-y bg-white"
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          disabled={isLoading}
          placeholder="Answer the questions in one concise response."
        />
        {validationError ? (
          <p role="alert" className="text-sm text-red-700">
            {validationError}
          </p>
        ) : null}
        <button className="button-primary" type="submit" disabled={isLoading}>
          {isLoading ? "Continuing…" : "Continue with clarification"}
        </button>
      </form>
    </section>
  );
}
