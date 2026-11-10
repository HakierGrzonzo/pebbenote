/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstructionsModel } from "../models/InstructionsModel";
import type { CancelablePromise } from "../core/CancelablePromise";
import type { BaseHttpRequest } from "../core/BaseHttpRequest";
export class InstructionsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * List Instructions
   * @returns InstructionsModel Successful Response
   * @throws ApiError
   */
  public listInstructions(): CancelablePromise<InstructionsModel> {
    return this.httpRequest.request({
      method: "GET",
      url: "/instruction/",
    });
  }
  /**
   * Replace Instructions
   * Replaces the standing instructions. Unless `apply` is false, the new ones
   * are then applied in the background to every note of the user that is not
   * changed in the meantime.
   * @param requestBody
   * @param apply
   * @returns InstructionsModel Successful Response
   * @throws ApiError
   */
  public replaceInstructions(
    requestBody: InstructionsModel,
    apply: boolean = true,
  ): CancelablePromise<InstructionsModel> {
    return this.httpRequest.request({
      method: "PUT",
      url: "/instruction/",
      query: {
        apply: apply,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
