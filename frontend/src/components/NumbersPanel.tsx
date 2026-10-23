import type { Numbers, Sizes } from "../types";

interface Props {
  sizes: Sizes | null;
  numbers: Numbers | null;
}

export function NumbersPanel({ sizes, numbers }: Props) {
  return (
    <section aria-label="Size, weight and cost">
      <h2>Size, weight and cost</h2>
      {sizes && (
        <dl className="numbers">
          <dt>US size</dt><dd>{sizes.us}</dd>
          <dt>UK size (approximate)</dt><dd>{sizes.uk}</dd>
          <dt>EU size</dt><dd>{sizes.eu}</dd>
          <dt>Inner diameter</dt><dd>{sizes.mm} mm</dd>
        </dl>
      )}
      {numbers ? (
        <>
          <dl className="numbers">
            <dt>Metal weight</dt><dd>{numbers.weight_g.toFixed(2)} g</dd>
            <dt>Metal cost range</dt><dd>{numbers.cost_text}</dd>
          </dl>
          <p className="muted small">
            Density {numbers.density_g_cm3} g/cm3. Prices: {numbers.price_source}, as of{" "}
            {numbers.price_as_of}.{numbers.prices_verified ? "" : " These prices have not been verified."}
          </p>
        </>
      ) : (
        <p className="muted">Weight and cost appear once the design can be built.</p>
      )}
    </section>
  );
}
