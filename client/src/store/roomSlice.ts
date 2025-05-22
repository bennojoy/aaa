import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Room, RoomList, RoomSearchParams } from '../types/room';

interface RoomState {
  rooms: Room[];
  total: number;
  loading: boolean;
  error: string | null;
}

const initialState: RoomState = {
  rooms: [],
  total: 0,
  loading: false,
  error: null,
};

const roomSlice = createSlice({
  name: 'room',
  initialState,
  reducers: {
    searchRoomsRequest: (state, action: PayloadAction<RoomSearchParams>) => {
      state.loading = true;
      state.error = null;
    },
    searchRoomsSuccess: (state, action: PayloadAction<RoomList>) => {
      state.loading = false;
      state.rooms = action.payload.items;
      state.total = action.payload.total;
    },
    searchRoomsFailure: (state, action: PayloadAction<string>) => {
      state.loading = false;
      state.error = action.payload;
    },
    clearRoomError: (state) => {
      state.error = null;
    },
  },
});

export const {
  searchRoomsRequest,
  searchRoomsSuccess,
  searchRoomsFailure,
  clearRoomError,
} = roomSlice.actions;

export default roomSlice.reducer; 