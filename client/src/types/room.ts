/**
 * Represents a chat room in the application
 */
export interface Room {
  /** Unique identifier for the room */
  id: string;
  /** Name of the room */
  name: string;
  /** Description of the room */
  description: string;
  /** ISO timestamp when the room was created */
  created_at: string;
  /** ISO timestamp when the room was last updated */
  updated_at: string;
  /** ID of the user who owns the room */
  owner_id: string;
}

/**
 * Response from the rooms API containing a list of rooms and pagination info
 */
export interface RoomList {
  /** Array of room objects */
  items: Room[];
  /** Total number of rooms matching the query */
  total: number;
  /** Number of rooms skipped (for pagination) */
  skip: number;
  /** Maximum number of rooms returned */
  limit: number;
}

/**
 * Parameters for searching rooms
 */
export interface RoomSearchParams {
  /** Optional search query to filter rooms by name */
  query?: string;
  /** Number of rooms to skip (for pagination) */
  skip?: number;
  /** Maximum number of rooms to return */
  limit?: number;
} 