import { TranscriptPanel } from './transcript-panel';
import React from 'react';
import { describe, it, expect } from 'vitest';

describe('TranscriptPanel Optimization', () => {
  it('is wrapped in React.memo', () => {
    // Check if the component is memoized
    // React.memo returns an object with $$typeof: Symbol.for('react.memo')

    const isMemo = (component: any) => {
      return component && component.$$typeof === Symbol.for('react.memo');
    };

    expect(isMemo(TranscriptPanel)).toBe(true);
  });
});
