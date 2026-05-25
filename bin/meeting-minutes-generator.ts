#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { MeetingMinutesStack } from '../lib/meeting-minutes-stack';

const app = new cdk.App();

new MeetingMinutesStack(app, 'MeetingMinutesStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
});

