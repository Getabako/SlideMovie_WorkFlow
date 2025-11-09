import { useCurrentFrame, Img } from "remotion";
import { staticFile } from "remotion";

const idleImages = [
  staticFile("idle1.png"),
  staticFile("idle2.png"),
  staticFile("idle3.png"),
  staticFile("idle4.png"),
  staticFile("idle5.png"),
  staticFile("idle6.png"),
];

export const Video = () => {
  const frame = useCurrentFrame();

  // 5フレームごとに画像を切り替える
  const idleImageIndex = Math.floor(frame / 5) % idleImages.length;
  const imageToShow = idleImages[idleImageIndex];

  return (
    <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center", backgroundColor: "green" }}>
      <Img src={imageToShow} style={{ height: "80%" }} />
    </div>
  );
};
