/**
 * Audio utility functions for Agora voice tutor
 */

export async function playAudioFromBase64(base64Data: string): Promise<void> {
  try {
    const audioData = `data:audio/mpeg;base64,${base64Data}`;
    const audio = new Audio(audioData);

    return new Promise((resolve, reject) => {
      audio.onended = () => resolve();
      audio.onerror = reject;
      audio.play().catch(reject);
    });
  } catch (error) {
    console.error('[Agora] Failed to play audio:', error);
    throw error;
  }
}

export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

export function getAudioDuration(blob: Blob): Promise<number> {
  return new Promise((resolve, reject) => {
    const audio = new Audio();
    const url = URL.createObjectURL(blob);
    audio.src = url;
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(audio.duration);
    };
    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load audio metadata'));
    };
  });
}
