import { useCurrentFrame, Img, Audio, useVideoConfig, staticFile, Sequence } from "remotion";

const idleImages = [
  staticFile("idle1.png"),
  staticFile("idle2.png"),
  staticFile("idle3.png"),
  staticFile("idle4.png"),
  staticFile("idle5.png"),
  staticFile("idle6.png"),
];

const talkImages = [
  staticFile("talk1.png"),
  staticFile("talk2.png"),
  staticFile("talk3.png"),
  staticFile("talk4.png"),
  staticFile("talk5.png"),
  staticFile("talk6.png"),
];

interface Subtitle {
  text: string;
  start: number;
  end: number;
  startFrame: number;
  endFrame: number;
}

interface SlideData {
  index: number;
  title: string;
  audioFile: string;
  duration: number;
  durationFrames: number;
  startTime: number;
  endTime: number;
  startFrame: number;
  endFrame: number;
  subtitles: Subtitle[];
  fullScript: string;
}

interface VideoProps {
  slides: SlideData[];
  fps: number;
  totalFrames: number;
}

export const Video: React.FC<VideoProps> = ({ slides, fps, totalFrames }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // 現在のスライドを見つける
  const currentSlide = slides.find(
    (slide) => frame >= slide.startFrame && frame < slide.endFrame
  );

  // 現在の字幕を見つける
  const currentSubtitle = currentSlide?.subtitles.find(
    (subtitle) => frame >= subtitle.startFrame && frame < subtitle.endFrame
  );

  // 音声が再生中かどうかを判定（簡易的に、スライドが存在する場合は話している）
  const isTalking = currentSlide !== undefined;

  // 使用する画像配列を選択
  const images = isTalking ? talkImages : idleImages;

  // 5フレームごとに画像を切り替える
  const imageIndex = Math.floor(frame / 5) % images.length;
  const imageToShow = images[imageIndex];

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#2d2d2d",
      }}
    >
      {/* キャラクター */}
      <div
        style={{
          flex: 1,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Img src={imageToShow} style={{ height: "80%" }} />
      </div>

      {/* 字幕 */}
      {currentSubtitle && (
        <div
          style={{
            position: "absolute",
            bottom: 100,
            left: 0,
            right: 0,
            textAlign: "center",
            padding: "20px 40px",
          }}
        >
          <div
            style={{
              display: "inline-block",
              backgroundColor: "rgba(0, 0, 0, 0.8)",
              color: "white",
              fontSize: 48,
              padding: "20px 40px",
              borderRadius: 10,
              maxWidth: "80%",
              lineHeight: 1.5,
              fontWeight: "bold",
              textShadow: "2px 2px 4px rgba(0,0,0,0.8)",
            }}
          >
            {currentSubtitle.text}
          </div>
        </div>
      )}

      {/* 音声 */}
      {slides.map((slide) => (
        <Sequence
          key={slide.index}
          from={slide.startFrame}
          durationInFrames={slide.durationFrames}
        >
          <Audio src={staticFile(slide.audioFile)} />
        </Sequence>
      ))}
    </div>
  );
};
