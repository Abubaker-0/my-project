export function errorMessage(error) {
  return error?.response?.data?.message || "Something went wrong. Try again.";
}

export function fieldErrors(error) {
  const details = error?.response?.data?.details;
  if (!Array.isArray(details)) {
    return {};
  }
  return Object.fromEntries(
    details
      .filter((item) => item?.field && item?.message)
      .map((item) => [item.field, item.message]),
  );
}
