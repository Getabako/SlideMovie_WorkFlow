import { Composition } from "remotion";
import { Video } from "./Video";

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="Video"
        component={Video}
        durationInFrames={150} // 5 seconds at 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
