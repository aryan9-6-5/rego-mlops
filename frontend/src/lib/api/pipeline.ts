import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { supabase } from '@/lib/auth/supabase';
import {
  applyGateEvent,
  isGateEvent,
  type PipelineRun,
} from './pipelineState';

const RUN_KEY = ['pipeline-run'] as const;
const RECONNECT_MS = 3000;
const FALLBACK_POLL_MS = 5000;

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const WS_URL = `${API_BASE.replace(/^http/, 'ws')}/pipeline/events`;

export function usePipelineRun() {
  return useQuery({
    queryKey: RUN_KEY,
    queryFn: async () => (await api.get<PipelineRun | null>('/pipeline/status')).data,
    refetchInterval: FALLBACK_POLL_MS,
  });
}

export function useSubmitModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (artifactPath: string) =>
      (await api.post<{ model_version: string }>('/pipeline/submit', {
        artifact_path: artifactPath,
      })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: RUN_KEY }),
  });
}

export function useTriggerCT() {
  return useMutation({
    mutationFn: async (regulationVersion: string) =>
      (await api.post<{ regulation_version: string }>('/pipeline/trigger-ct', {
        regulation_version: regulationVersion,
      })).data,
  });
}

/** Live gate events over WebSocket. Returns whether the socket is connected.
 * The JWT is sent as the first message, never in the URL. */
export function usePipelineSocket(): boolean {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let timer: number | undefined;
    let stopped = false;

    const connect = async () => {
      const { data } = await supabase.auth.getSession();
      if (stopped || !data.session) return;
      const token = data.session.access_token;
      socket = new WebSocket(WS_URL);
      socket.onopen = () => {
        socket?.send(JSON.stringify({ token }));
        setConnected(true);
      };
      socket.onmessage = (message: MessageEvent<string>) => {
        const parsed: unknown = JSON.parse(message.data);
        if (!isGateEvent(parsed)) return;
        const current = queryClient.getQueryData<PipelineRun | null>(RUN_KEY);
        const next = current ? applyGateEvent(current, parsed) : null;
        if (next) queryClient.setQueryData(RUN_KEY, next);
        else void queryClient.invalidateQueries({ queryKey: RUN_KEY });
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) timer = window.setTimeout(connect, RECONNECT_MS);
      };
    };

    void connect();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [queryClient]);

  return connected;
}
