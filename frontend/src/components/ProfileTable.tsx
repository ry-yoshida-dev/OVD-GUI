import type { Profile } from "../api/types";
import { useDialogs } from "./DialogHost";

interface ProfileTableProps {
  profiles: Profile[];
  shownKey: string | null;
  comparedKey: string | null;
  onSelect: (key: string) => void;
  onRemove: (key: string) => void;
}

export function ProfileTable({ profiles, shownKey, comparedKey, onSelect, onRemove }: ProfileTableProps) {
  const dialogs = useDialogs();
  const shown = profiles.find((profile) => profile.key === shownKey);
  const remove = async () => {
    if (shown === undefined) return;
    const isConfirmed = await dialogs.confirm({
      title: "Remove Model Results",
      message: `Forget the ${shown.detection_count} detections of ${shown.model_name} (${shown.options_text}) on ${shown.image_count} images?`,
      confirmLabel: "Remove",
      isDanger: true,
    });
    if (isConfirmed) onRemove(shown.key);
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
      <div className="panel-title">
        <span className="grow">Models</span>
        <button className="small" disabled={shown === undefined} onClick={() => void remove()}>
          Remove
        </button>
      </div>
      <div
        className="table-wrap"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Delete" || event.key === "Backspace") void remove();
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            const index = profiles.findIndex((profile) => profile.key === shownKey);
            const next = profiles[Math.max(0, Math.min(profiles.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)))];
            if (next !== undefined && next.key !== shownKey) onSelect(next.key);
          }
        }}
      >
        <table className="grid">
          <colgroup>
            <col style={{ width: 96 }} />
            <col style={{ width: 150 }} />
            <col style={{ width: 52 }} />
            <col style={{ width: 48 }} />
            <col style={{ width: 46 }} />
            <col style={{ width: 46 }} />
            <col style={{ width: 58 }} />
            <col style={{ width: 66 }} />
            <col style={{ width: 76 }} />
          </colgroup>
          <thead>
            <tr>
              <th>Backend</th>
              <th>Model</th>
              <th>Device</th>
              <th>Prec.</th>
              <th>Conf</th>
              <th>NMS</th>
              <th>Images</th>
              <th>Outdated</th>
              <th>Detections</th>
            </tr>
          </thead>
          <tbody>
            {profiles.length === 0 && (
              <tr className="status">
                <td colSpan={9}>No results yet. Open images and detect to fill this table.</td>
              </tr>
            )}
            {profiles.map((profile) => (
              <tr
                key={profile.key}
                className={profile.key === shownKey ? "selected" : ""}
                onClick={() => onSelect(profile.key)}
                title={profile.weights_path}
              >
                <td>{profile.backend}</td>
                <td>
                  {profile.model_name}
                  {profile.key === comparedKey && <span className="badge" style={{ marginLeft: 6 }}>compared</span>}
                </td>
                <td>{profile.device}</td>
                <td>{profile.precision}</td>
                <td className="number">{profile.confidence}</td>
                <td className="number">{profile.nms}</td>
                <td className="number">{profile.image_count}</td>
                <td className="number" style={{ color: profile.outdated_image_count > 0 ? "var(--warning)" : undefined }}>
                  {profile.outdated_image_count}
                </td>
                <td className="number">{profile.detection_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
