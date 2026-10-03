import type { CityView } from "../types/game";
import { who } from "./labels";

interface Props {
  city: CityView | undefined;
  // True when the person looking at the screen is the seller.
  isYou?: boolean;
  size?: "sm" | "lg";
}

/** Makes the seller of a lot unmistakable wherever a lot is shown. */
export default function SellerTag({ city, isYou, size = "sm" }: Props) {
  const big = size === "lg";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border border-amber-300/40 bg-amber-400/10 ${
        big ? "px-4 py-1.5 text-lg" : "px-2 py-0.5 text-xs"
      }`}
    >
      <span className={`uppercase tracking-widest text-amber-300/80 ${big ? "text-xs" : "text-[10px]"}`}>
        Seller
      </span>
      <span className="font-semibold text-amber-100">{isYou ? "You" : who(city)}</span>
    </span>
  );
}
