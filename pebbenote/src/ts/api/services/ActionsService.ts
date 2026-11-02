/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ActionAcceptedModel } from "../models/ActionAcceptedModel";
import type { ActionEditModel } from "../models/ActionEditModel";
import type { NoteModel } from "../models/NoteModel";
import type { CancelablePromise } from "../core/CancelablePromise";
import type { BaseHttpRequest } from "../core/BaseHttpRequest";
export class ActionsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Apply Action
   * @param requestBody
   * @returns NoteModel Successful Response
   * @returns ActionAcceptedModel Still applying, poll the note with If-Modified-Since
   * @throws ApiError
   */
  public applyAction(
    requestBody: ActionEditModel,
  ): CancelablePromise<NoteModel | ActionAcceptedModel> {
    return this.httpRequest.request({
      method: "POST",
      url: "/action/",
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
