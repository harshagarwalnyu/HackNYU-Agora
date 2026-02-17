export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];

  async initialize(): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: 'audio/webm',
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.chunks.push(event.data);
        }
      };
    } catch (error) {
      console.error('[Agora] Failed to initialize audio recorder:', error);
      throw error;
    }
  }

  start(): void {
    if (!this.mediaRecorder) throw new Error('Recorder not initialized');
    this.chunks = [];
    this.mediaRecorder.start();
  }

  async stop(): Promise<Blob | null> {
    if (!this.mediaRecorder) throw new Error('Recorder not initialized');

    return new Promise((resolve) => {
      if (!this.mediaRecorder) return resolve(null);

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.chunks, { type: 'audio/webm' });
        
        // Ensure minimum size (approx 0.1s of audio)
        // 1 second of 16khz mono 16-bit audio is ~32kb uncompressed
        // webm/opus is compressed, but header overhead exists.
        // Groq says >0.01s. Let's aim for >1KB to be safe and meaningful.
        if (blob.size < 1024) { 
            console.warn('[AudioRecorder] Audio too short/empty, discarding', blob.size);
            resolve(null);
        } else {
            resolve(blob);
        }
      };

      this.mediaRecorder.stop();
    });
  }

  async getAudioContext(): Promise<AudioContext> {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (this.stream) {
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(this.stream);
      source.connect(analyser);
    }
    return audioContext;
  }

  cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
  }
}
