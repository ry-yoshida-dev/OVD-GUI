import type { ReactNode } from "react";

interface SectionProps {
  title: ReactNode;
  isCollapsed: boolean;
  onToggle: () => void;
  isStretched?: boolean;
  actions?: ReactNode;
  children: ReactNode;
}

export function Section({ title, isCollapsed, onToggle, isStretched = false, actions, children }: SectionProps) {
  return (
    <div className={`section${isStretched && !isCollapsed ? " stretched" : ""}${isCollapsed ? " collapsed" : ""}`}>
      <div className="section-header" onClick={onToggle}>
        <span className="chevron">▾</span>
        <span className="grow">{title}</span>
        {actions !== undefined && <span onClick={(event) => event.stopPropagation()}>{actions}</span>}
      </div>
      {!isCollapsed && <div className="section-body">{children}</div>}
    </div>
  );
}
