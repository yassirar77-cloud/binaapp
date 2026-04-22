interface AuthInputProps {
  label: string
  id: string
  type?: string
  name?: string
  value?: string
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string
  autoComplete?: string
  required?: boolean
  helperText?: string
}

export default function AuthInput({
  label,
  id,
  type = 'text',
  name,
  value,
  onChange,
  placeholder,
  autoComplete,
  required,
  helperText,
}: AuthInputProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block font-geist text-sm font-medium text-ink-300 mb-2"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
        className="w-full bg-ink-700 border border-white/10 rounded-xl px-4 py-3 font-geist text-sm text-white placeholder:text-ink-400 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors"
      />
      {helperText && (
        <p className="mt-1.5 font-geist text-xs text-ink-400">{helperText}</p>
      )}
    </div>
  )
}
