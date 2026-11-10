/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NoteModel } from "../models/NoteModel";
import type { NoteUpdateModel } from "../models/NoteUpdateModel";
import type { NoteViewModel } from "../models/NoteViewModel";
import type { CancelablePromise } from "../core/CancelablePromise";
import type { BaseHttpRequest } from "../core/BaseHttpRequest";
export class NotesService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * List Notes
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public listNotes(): CancelablePromise<Array<NoteModel>> {
    return this.httpRequest.request({
      method: "GET",
      url: "/note/",
    });
  }
  /**
   * Create Note
   * @param content
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public createNote(content: string): CancelablePromise<NoteModel> {
    return this.httpRequest.request({
      method: "POST",
      url: "/note/",
      query: {
        content: content,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get Note By Id
   * @param noteId
   * @param ifModifiedSince
   * @returns NoteViewModel Successful Response
   * @throws ApiError
   */
  public getNoteById(
    noteId: string,
    ifModifiedSince?: string | null,
  ): CancelablePromise<NoteViewModel> {
    return this.httpRequest.request({
      method: "GET",
      url: "/note/{note_id}",
      path: {
        note_id: noteId,
      },
      headers: {
        "if-modified-since": ifModifiedSince,
      },
      errors: {
        304: `Not modified`,
        422: `Validation Error`,
      },
    });
  }
  /**
   * Edit Note By Id
   * @param noteId
   * @param requestBody
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public editNoteById(
    noteId: string,
    requestBody: NoteUpdateModel,
  ): CancelablePromise<NoteModel> {
    return this.httpRequest.request({
      method: "PATCH",
      url: "/note/{note_id}",
      path: {
        note_id: noteId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        409: `The note has changed since base_version`,
        422: `Validation Error`,
      },
    });
  }
  /**
   * Set Default Note
   * @param noteId
   * @returns NoteModel Successful Response
   * @throws ApiError
   */
  public setDefaultNote(noteId: string): CancelablePromise<NoteModel> {
    return this.httpRequest.request({
      method: "PUT",
      url: "/note/{note_id}/default",
      path: {
        note_id: noteId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
