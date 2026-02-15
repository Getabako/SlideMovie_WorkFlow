import { useCurrentFrame, Img, staticFile, AbsoluteFill, Audio, Sequence } from "remotion";
import "./fonts.css";

// レイアウト定数（背景画像に合わせた座標）
const LAYOUT = {
  // スライド領域（16:9）
  slide: {
    x: 10,
    y: 55,
    width: 1395,
    height: 785, // 1395 * 9 / 16 = 784.6875
  },
  // タイトルスクロール領域（スライドの上）
  titleScroll: {
    x: 10,
    y: 5,
    width: 1395,
    height: 45,
  },
  // 字幕領域（グレーの四角内）
  subtitle: {
    x: 40,
    y: 910,
    width: 1355,
    height: 155,
    padding: 20,
  },
  // キャラクター位置（右下、下半身見切れ）
  character: {
    right: 0,
    bottom: -150, // 下半身を画面外に
    height: 600,
  },
};

interface Subtitle {
  text: string;
  startFrame: number;
  endFrame: number;
}

interface SlideData {
  slide: number;
  startFrame: number;
  endFrame: number;
  audioFile: string;
  audioStartFrame: number;
  audioDuration: number;
  subtitles: Subtitle[];
  title?: string;
}

interface VideoProps {
  slides: SlideData[];
}

// タイトルスクロールコンポーネント
const TitleScroller: React.FC<{ title: string; frame: number }> = ({ title, frame }) => {
  const scrollSpeed = 2;
  const textWidth = title.length * 40;
  const totalWidth = LAYOUT.titleScroll.width + textWidth;
  const offset = (frame * scrollSpeed) % totalWidth;

  return (
    <div
      style={{
        position: "absolute",
        left: LAYOUT.titleScroll.x,
        top: LAYOUT.titleScroll.y,
        width: LAYOUT.titleScroll.width,
        height: LAYOUT.titleScroll.height,
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          whiteSpace: "nowrap",
          transform: `translateX(${LAYOUT.titleScroll.width - offset}px)`,
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              color: "#4a4a4a",
              fontSize: 28,
              fontWeight: 700,
              fontFamily: "'M PLUS 2', 'Noto Sans JP', sans-serif",
              marginRight: 100,
            }}
          >
            {title}
          </span>
        ))}
      </div>
    </div>
  );
};

// RPG風字幕コンポーネント
const RPGSubtitle: React.FC<{ text: string }> = ({ text }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: LAYOUT.subtitle.x,
        top: LAYOUT.subtitle.y,
        width: LAYOUT.subtitle.width,
        height: LAYOUT.subtitle.height,
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-start",
        padding: `${LAYOUT.subtitle.padding}px ${LAYOUT.subtitle.padding + 20}px`,
        boxSizing: "border-box",
        zIndex: 4,
      }}
    >
      <div
        style={{
          color: "white",
          fontSize: 36,
          lineHeight: 1.5,
          fontWeight: 700,
          fontFamily: "'M PLUS 2', 'Noto Sans JP', 'Hiragino Sans', sans-serif",
          textShadow: "2px 2px 4px rgba(0,0,0,0.8), -1px -1px 2px rgba(0,0,0,0.8)",
          maxWidth: "100%",
          wordBreak: "keep-all",
          overflowWrap: "break-word",
        }}
      >
        {text}
      </div>
    </div>
  );
};

// スライドタイトルを字幕から推測する関数
const extractTitleFromSubtitles = (subtitles: Subtitle[]): string => {
  if (!subtitles || subtitles.length === 0) return "講座";
  const firstText = subtitles[0].text;
  const match = firstText.match(/^[^。、！？!?,\.]+/);
  return match ? match[0] : firstText.slice(0, 20);
};

export const VideoITAI: React.FC<VideoProps> = ({ slides }) => {
  const frame = useCurrentFrame();

  // 現在のスライドを見つける
  const currentSlide = slides.find(
    (slide) => frame >= slide.startFrame && frame < slide.endFrame
  );

  // 現在の字幕を見つける
  const currentSubtitle = currentSlide?.subtitles.find(
    (subtitle) => frame >= subtitle.startFrame && frame < subtitle.endFrame
  );

  // キャラクターアニメーション
  const idleImages = ["idle1.png", "idle2.png", "idle3.png", "idle4.png", "idle5.png", "idle6.png"];
  const talkImages = ["talk1.png", "talk2.png", "talk3.png", "talk4.png", "talk5.png", "talk6.png"];
  const isTalking = currentSubtitle !== undefined;
  const images = isTalking ? talkImages : idleImages;
  const animationSpeed = isTalking ? 3 : 5;
  const imageIndex = Math.floor(frame / animationSpeed) % images.length;

  // スライド画像パス
  const slideImagePath = currentSlide
    ? `slides_it_ai/slide_${String(currentSlide.slide).padStart(3, '0')}.png`
    : null;

  // スライドタイトルを取得
  const slideTitle = currentSlide?.title || extractTitleFromSubtitles(currentSlide?.subtitles || []);

  return (
    <AbsoluteFill style={{ backgroundColor: "#2d2d2d" }}>
      {/* 音声 */}
      {slides.map((slide) => (
        <Sequence key={slide.slide} from={slide.audioStartFrame} durationInFrames={Math.ceil(slide.audioDuration * 30) + 30}>
          <Audio src={staticFile(slide.audioFile)} />
        </Sequence>
      ))}

      {/* 背景画像 */}
      <Img
        src={staticFile("background.png")}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          zIndex: 0,
        }}
      />

      {/* タイトルスクロール（スライド上部） */}
      {currentSlide && (
        <TitleScroller title={slideTitle} frame={frame} />
      )}

      {/* スライド画像（16:9エリアにピッタリ配置） */}
      {slideImagePath && (
        <div
          style={{
            position: "absolute",
            left: LAYOUT.slide.x,
            top: LAYOUT.slide.y,
            width: LAYOUT.slide.width,
            height: LAYOUT.slide.height,
            zIndex: 1,
            overflow: "hidden",
          }}
        >
          <Img
            src={staticFile(slideImagePath)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
            }}
          />
        </div>
      )}

      {/* キャラクター（右下、下半身見切れ） */}
      <div
        style={{
          position: "absolute",
          bottom: LAYOUT.character.bottom,
          right: LAYOUT.character.right,
          height: LAYOUT.character.height,
          zIndex: 3,
        }}
      >
        <Img src={staticFile(images[imageIndex])} style={{ height: "100%" }} />
      </div>

      {/* 字幕（RPG風メッセージウィンドウ） */}
      {currentSubtitle && (
        <RPGSubtitle text={currentSubtitle.text} />
      )}
    </AbsoluteFill>
  );
};
