import type { CityView } from "../types/game";

/** Who owns a city, for sale messages: "Ana at Babylon", or "Troy (AI)". */
export function merchantLabel(city: CityView | undefined): string {
  if (!city) return "?";
  if (city.is_ai || !city.owner_name) return `${city.name} (AI)`;
  return `${city.owner_name} at ${city.name}`;
}

/** Short label for who is acting: the player's name, or "🤖 Troy" for AI cities. */
export function who(city: CityView | undefined): string {
  if (!city) return "?";
  if (city.is_ai || !city.owner_name) return `🤖 ${city.name}`;
  return city.owner_name;
}
