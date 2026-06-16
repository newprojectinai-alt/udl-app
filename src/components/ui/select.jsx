export function Select({ value, onValueChange, disabled, children }) {
  const options = [];
  const collect = (node) => {
    if (!node) return;
    if (Array.isArray(node)) return node.forEach(collect);
    if (node.props?.value) options.push({ value: node.props.value, label: node.props.children });
    collect(node.props?.children);
  };
  collect(children);
  return (
    <select disabled={disabled} value={value || ''} onChange={(event) => onValueChange?.(event.target.value)} className="w-full h-10 rounded-xl border border-input bg-background px-3 text-sm">
      <option value="">Select</option>
      {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
    </select>
  );
}

export function SelectTrigger({ children }) { return children; }
export function SelectValue() { return null; }
export function SelectContent({ children }) { return children; }
export function SelectItem({ value, children }) { return <option value={value}>{children}</option>; }
