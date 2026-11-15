import { Button } from "./Button";

export function ErrorState({ title = "This page could not be loaded", body, onRetry }) {
  return (
    <div className="px-6 py-12 text-center" role="alert">
      <p className="font-serif text-xl text-ink-950">{title}</p>
      {body ? <p className="mx-auto mt-2 max-w-md text-sm text-ink-700">{body}</p> : null}
      {onRetry ? (
        <Button className="mt-4" variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
