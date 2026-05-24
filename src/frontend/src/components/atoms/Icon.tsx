interface IconProps {
  name: "send" | "info" | "attention" | "retry";
}

const icons: Record<IconProps["name"], string> = {
  send: "->",
  info: "i",
  attention: "!",
  retry: "R"
};

export function Icon({ name }: IconProps) {
  return (
    <span aria-hidden="true" className={`icon icon--${name}`}>
      {icons[name]}
    </span>
  );
}
