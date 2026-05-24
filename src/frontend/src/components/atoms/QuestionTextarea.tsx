import type { TextareaHTMLAttributes } from "react";

interface QuestionTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export function QuestionTextarea({ label, className = "", ...props }: QuestionTextareaProps) {
  return (
    <label className="question-field">
      <span className="visually-hidden">{label}</span>
      <textarea className={`question-textarea ${className}`.trim()} rows={1} {...props} />
    </label>
  );
}
