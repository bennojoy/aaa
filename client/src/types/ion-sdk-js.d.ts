declare module 'ion-sdk-js/dist/json-rpc.min.js' {
  export class IonSFUJSONRPCSignal {
    constructor(url: string);
    onclose?: () => void;
    onerror?: (error: Error) => void;
    onmessage?: (message: any) => void;
    send(message: any): void;
    close(): void;
  }
}

declare module 'ion-sdk-js/dist/ion-sdk.min.js' {
  import { IonSFUJSONRPCSignal } from 'ion-sdk-js/dist/json-rpc.min.js';

  export interface ClientConfig {
    codec?: string;
    iceServers?: RTCIceServer[];
  }

  export class Client {
    constructor(signal: IonSFUJSONRPCSignal, config?: ClientConfig);
    ontrack?: (track: MediaStreamTrack, stream: MediaStream) => void;
    ondatachannel?: (ev: RTCDataChannelEvent) => void;
    onspeaker?: (speakers: string[]) => void;
    onerrnegotiate?: (role: string, err: Error, offer: RTCSessionDescriptionInit, answer: RTCSessionDescriptionInit) => void;
    onactivelayer?: (layer: string) => void;
    join(roomId: string, userId: string): Promise<void>;
    leave(): void;
    publish(stream: LocalStream): void;
    close(): void;
  }

  export class LocalStream {
    id: string;
    constructor(stream: MediaStream);
    static getUserMedia(options: {
      resolution?: string;
      codec?: string;
      audio?: boolean;
      video?: boolean;
      simulcast?: boolean;
    }): Promise<LocalStream>;
    getTracks(): MediaStreamTrack[];
    getAudioTracks(): MediaStreamTrack[];
    getVideoTracks(): MediaStreamTrack[];
    switchDevice(kind: 'audio' | 'video', deviceId: string): Promise<void>;
  }
} 