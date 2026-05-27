export function LoadingScreen() {
  return (
    <div
      className="fixed inset-0 flex flex-col items-center justify-center gap-3"
      style={{ background: "#0d1117" }}
    >
      <div
        style={{
          width: 24,
          height: 24,
          borderRadius: "50%",
          border: "2px solid #21262d",
          borderTopColor: "#1f6feb",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <span style={{ fontSize: 12, color: "#6e7681", fontFamily: "'Inter', sans-serif" }}>
        REU Secure
      </span>
    </div>
  );
}
