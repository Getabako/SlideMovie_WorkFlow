import { Composition } from "remotion";
import { Video } from "./Video";

// タイミングデータをインポート
// ビルド時にこのファイルが存在することを前提としています
let timingsData: any;
try {
  timingsData = require("../timings.json");
} catch (error) {
  // デフォルトのデータ（開発時用）
  timingsData = {
    fps: 30,
    totalFrames: 150,
    slides: [],
  };
}

export const RemotionRoot = () => {
  const { fps, totalFrames, slides } = timingsData;

  return (
    <>
      <Composition
        id="Video"
        component={Video}
        durationInFrames={totalFrames || 150}
        fps={fps || 30}
        width={1920}
        height={1080}
        defaultProps={{
          slides: slides || [],
          fps: fps || 30,
          totalFrames: totalFrames || 150,
        }}
      />
    </>
  );
};
