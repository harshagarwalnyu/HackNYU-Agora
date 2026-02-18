import { create } from 'zustand';
import { Material } from '../services/materials-api';

interface UploadingFile {
    filename: string;
    progress: number;
}

interface MaterialsState {
    materials: Material[];
    uploadingFiles: Map<string, UploadingFile>;
    setMaterials: (materials: Material[]) => void;
    addMaterial: (material: Material) => void;
    updateMaterial: (jobId: string, updates: Partial<Material>) => void;
    removeMaterial: (jobId: string) => void;
    addUploadingFile: (id: string, filename: string) => void;
    updateUploadProgress: (id: string, progress: number) => void;
    removeUploadingFile: (id: string) => void;
}

export const useMaterialsStore = create<MaterialsState>((set) => ({
    materials: [],
    uploadingFiles: new Map(),

    setMaterials: (materials: Material[]) => set({ materials }),

    addMaterial: (material: Material) =>
        set((state: MaterialsState) => ({
            materials: [material, ...state.materials],
        })),

    updateMaterial: (jobId: string, updates: Partial<Material>) =>
        set((state: MaterialsState) => ({
            materials: state.materials.map((m: Material) =>
                m.job_id === jobId ? { ...m, ...updates } : m
            ),
        })),

    removeMaterial: (jobId: string) =>
        set((state: MaterialsState) => ({
            materials: state.materials.filter((m: Material) => m.job_id !== jobId),
        })),

    addUploadingFile: (id: string, filename: string) =>
        set((state: MaterialsState) => {
            const newMap = new Map(state.uploadingFiles);
            newMap.set(id, { filename, progress: 0 });
            return { uploadingFiles: newMap };
        }),

    updateUploadProgress: (id: string, progress: number) =>
        set((state: MaterialsState) => {
            const newMap = new Map(state.uploadingFiles);
            const file = newMap.get(id);
            if (file) {
                newMap.set(id, { ...file, progress });
            }
            return { uploadingFiles: newMap };
        }),

    removeUploadingFile: (id: string) =>
        set((state: MaterialsState) => {
            const newMap = new Map(state.uploadingFiles);
            newMap.delete(id);
            return { uploadingFiles: newMap };
        }),
}));
