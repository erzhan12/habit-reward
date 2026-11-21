/**
 * What was completed on one day, for the History day detail (feature 0049).
 *
 * @param {Object<string, string[]>} completions  { habitId: ["YYYY-MM-DD", ...] } — keys arrive as strings
 * @param {{id: number|string, name: string}[]} habits  active habits (names to show)
 * @param {string} isoDate  "YYYY-MM-DD"
 * @returns {{count: number, names: string[], otherCount: number}}
 *   names: active habits completed that day, in `habits` order;
 *   otherCount: completions of habits not in `habits` (e.g. deactivated).
 */
export function dayCompletions(completions, habits, isoDate) {
  const doneIds = new Set();
  for (const [habitId, dates] of Object.entries(completions || {})) {
    if (Array.isArray(dates) && dates.includes(isoDate)) doneIds.add(String(habitId));
  }

  const names = [];
  const known = new Set();
  for (const habit of habits || []) {
    const id = String(habit.id);
    known.add(id);
    if (doneIds.has(id)) names.push(habit.name);
  }

  let otherCount = 0;
  for (const id of doneIds) if (!known.has(id)) otherCount += 1;

  return { count: doneIds.size, names, otherCount };
}
