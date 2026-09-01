import type { ReactNode } from "react";

/** Panel: pembungkus baku setiap blok pada dashboard. */
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={["panel flex flex-col", className].filter(Boolean).join(" ")}>
      <div className="panel-header">
        <h2 className="panel-title">{title}</h2>
        {action}
      </div>
      <div className={["panel-body flex-1", bodyClassName].filter(Boolean).join(" ")}>
        {children}
      </div>
    </section>
  );
}
