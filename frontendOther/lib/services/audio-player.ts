export class AudioPlayer {
  private audioQueue: string[] = [];
  private currentAudio: HTMLAudioElement | null = null;
  private isPlaying: boolean = false;

  play(audioData: string): void {
    this.audioQueue.push(audioData);
    this.processQueue();
  }

  stop(): void {
    // Clear queue
    this.audioQueue = [];
    
    // Stop current audio
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    
    this.isPlaying = false;
  }

  private processQueue(): void {
    if (this.isPlaying || this.audioQueue.length === 0) {
      return;
    }

    this.isPlaying = true;
    const nextAudioData = this.audioQueue.shift();

    if (nextAudioData) {
      this.currentAudio = new Audio(nextAudioData);
      
      this.currentAudio.onended = () => {
        this.isPlaying = false;
        this.currentAudio = null;
        this.processQueue(); // Play next
      };

      this.currentAudio.onerror = (e) => {
        console.error('[AudioPlayer] Playback error:', e);
        this.isPlaying = false;
        this.currentAudio = null;
        this.processQueue(); // Try next
      };

      this.currentAudio.play().catch((err) => {
        console.error('[AudioPlayer] Play failed:', err);
        this.isPlaying = false;
        this.currentAudio = null;
        this.processQueue();
      });
    }
  }
}

export const audioPlayer = new AudioPlayer();
